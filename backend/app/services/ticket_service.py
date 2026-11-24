from __future__ import annotations

import base64
import hashlib
import hmac
import io
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.repositories import ticket_repo

VALIDATION_TTL_SECONDS = 5


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _sign(ticket_id: str) -> str:
    return hmac.new(
        settings.TICKET_HMAC_SECRET.encode("utf-8"),
        ticket_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _ticket_code(ticket_id: str) -> tuple[str, str]:
    signature = _sign(ticket_id)
    return f"{ticket_id}.{signature}", signature


def _qr_data_uri(code: str) -> str:
    try:
        import qrcode

        qr = qrcode.QRCode(version=1, box_size=8, border=4)
        qr.add_data(code)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except ImportError:
        return code


def emit_tickets(db, redis_cli, order: dict, reservation: dict) -> list[dict]:
    existing = ticket_repo.find_by_order(db, order["_id"])
    if existing:
        return existing

    emitted: list[dict] = []
    for item in order.get("items", []):
        seat = item.get("silla")
        if seat:
            copies = 1
        else:
            copies = int(item.get("cantidad", 1))

        for _ in range(copies):
            ticket_id = f"bol_{uuid.uuid4().hex[:12]}"
            code, signature = _ticket_code(ticket_id)
            ticket = {
                "_id": ticket_id,
                "codigo": code,
                "firma": signature,
                "qr": _qr_data_uri(code),
                "ordenId": order["_id"],
                "compradorId": order["compradorId"],
                "funcionId": order["funcionId"],
                "seccion": item["seccion"],
                "silla": seat,
                "cantidad": 1,
                "precio": float(item["precioUnitario"]),
                "estado": "valida",
                "emitidaEn": order["fechaCreacion"],
                "usadaEn": None,
            }
            try:
                emitted.append(ticket_repo.insert(db, ticket))
                if seat:
                    redis_cli.delete(
                        f"lock:silla:{order['funcionId']}:{seat}"
                    )
            except DuplicateKeyError:
                duplicate = ticket_repo.find_by_code(db, code)
                if duplicate:
                    emitted.append(duplicate)

    return emitted


def get(db, ticket_id: str, user: dict) -> dict:
    ticket = ticket_repo.find_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Boleta no encontrada")
    if user["rol"] not in ("administrador", "validador") and ticket["compradorId"] != user["_id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La boleta pertenece a otro usuario")
    return _with_event_info(db, ticket)


def _with_event_info(db, ticket: dict) -> dict:
    enriched = dict(ticket)
    funcion_id = ticket.get("funcionId")
    enriched["eventoDisponible"] = False
    enriched["eventoNombre"] = None
    enriched["eventoId"] = None
    enriched["eventoCategoria"] = None
    enriched["eventoFechaHora"] = None
    enriched["recintoId"] = None
    enriched["recintoNombre"] = None
    enriched["recintoCiudad"] = None

    event_collection = getattr(db, "eventos", None)
    if event_collection is None or not funcion_id:
        return enriched

    event = event_collection.find_one({"funciones.funcionId": funcion_id})
    if not event:
        return enriched

    show = next(
        (
            funcion
            for funcion in event.get("funciones", [])
            if funcion.get("funcionId") == funcion_id
        ),
        None,
    )
    if not show:
        return enriched

    enriched["eventoDisponible"] = True
    enriched["eventoNombre"] = event.get("nombre")
    enriched["eventoId"] = event.get("_id")
    enriched["eventoCategoria"] = event.get("categoria")
    enriched["eventoFechaHora"] = show.get("fechaHora")
    enriched["recintoId"] = show.get("recintoId")
    enriched["recintoCiudad"] = show.get("ciudad")

    venue_collection = getattr(db, "recintos", None)
    if venue_collection is not None:
        venue = venue_collection.find_one({"_id": show.get("recintoId")})
        if venue:
            enriched["recintoNombre"] = venue.get("nombre")
            if not enriched["recintoCiudad"]:
                enriched["recintoCiudad"] = venue.get("ciudad")
    return enriched


def get_by_buyer(db, buyer_id: str, user: dict) -> list[dict]:
    if user["rol"] not in ("administrador",) and user["_id"] != buyer_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No puede consultar las boletas de otro usuario",
        )
    tickets = ticket_repo.find_by_buyer(db, buyer_id)
    return [_with_event_info(db, ticket) for ticket in tickets]


def get_all(db, user: dict) -> list[dict]:
    if user["rol"] not in ("administrador", "validador"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo administradores y validadores pueden consultar todas las boletas",
        )
    tickets = ticket_repo.find_all(db)
    return [_with_event_info(db, ticket) for ticket in tickets]


def _record_attempt(
    db,
    ticket_id: str | None,
    code: str,
    result: str,
    puerta: str,
    validator_id: str | None,
) -> dict:
    attempt = {
        "_id": f"val_{uuid.uuid4().hex[:12]}",
        "boletaId": ticket_id,
        "codigoPresentado": code,
        "resultado": result,
        "puerta": puerta,
        "validadorId": validator_id,
        "fecha": _iso(_now()),
    }
    db.validaciones.insert_one(attempt)
    return attempt


def validate(db, redis_cli, user: dict, data: dict) -> dict:
    code = data["codigo"].strip()
    puerta = data["puerta"].strip()

    ticket_id: str | None = None
    if "." in code:
        ticket_id = code.split(".", 1)[0]

    ticket = ticket_repo.find_by_id(db, ticket_id) if ticket_id else None
    if not ticket:
        attempt = _record_attempt(
            db, None, code, "boleta_no_encontrada", puerta, user["_id"]
        )
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            {"detail": "Código de boleta no encontrado", "validacion": attempt},
        )

    expected_code, _ = _ticket_code(ticket["_id"])
    if not hmac.compare_digest(code, expected_code):
        attempt = _record_attempt(
            db, ticket["_id"], code, "firma_invalida", puerta, user["_id"]
        )
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"detail": "Firma de boleta inválida", "validacion": attempt},
        )

    lock_key = f"lock:validacion:{ticket['_id']}"
    acquired = redis_cli.set(
        lock_key,
        user["_id"],
        nx=True,
        ex=VALIDATION_TTL_SECONDS,
    )
    if not acquired:
        attempt = _record_attempt(
            db,
            ticket["_id"],
            code,
            "validacion_concurrente",
            puerta,
            user["_id"],
        )
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"detail": "Validación concurrente", "validacion": attempt},
        )

    try:
        state = ticket.get("estado")
        if state != "valida":
            result = {
                "valida": "ya_usada",
                "usada": "ya_usada",
                "devuelta": "boleta_devuelta",
                "anulada": "boleta_anulada",
            }.get(state, "estado_invalido")
            attempt = _record_attempt(
                db,
                ticket["_id"],
                code,
                result,
                puerta,
                user["_id"],
            )
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                {"detail": "Boleta no válida", "resultado": result, "validacion": attempt},
            )

        used_at = _iso(_now())
        updated = ticket_repo.mark_used(db, ticket["_id"], used_at)
        if not updated:
            attempt = _record_attempt(
                db,
                ticket["_id"],
                code,
                "ya_usada",
                puerta,
                user["_id"],
            )
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                {"detail": "La boleta ya fue utilizada", "validacion": attempt},
            )

        attempt = _record_attempt(
            db,
            ticket["_id"],
            code,
            "aceptada",
            puerta,
            user["_id"],
        )
        return {
            "resultado": "aceptada",
            "boleta": updated,
            "validacion": attempt,
        }
    finally:
        redis_cli.delete(lock_key)
