from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _find_event(db, funcion_id: str) -> tuple[dict, dict]:
    event = db.eventos.find_one({"funciones.funcionId": funcion_id})
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Función no encontrada")
    show = next(
        (
            function
            for function in event.get("funciones", [])
            if function.get("funcionId") == funcion_id
        ),
        None,
    )
    if not show:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Función no encontrada")
    return event, show


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _policy_allows(db, ticket: dict) -> str | None:
    event, show = _find_event(db, ticket["funcionId"])
    organizer = db.organizadores.find_one({"_id": event["organizadorId"]})
    if not organizer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organizador no encontrado")

    policy = organizer.get("politicaDevolucion", "sin_devolucion")
    if policy == "sin_devolucion":
        return "El organizador no permite devoluciones"

    if policy == "hasta_48h_antes":
        show_date = _parse_datetime(show["fechaHora"])
        if show_date <= _now() + timedelta(hours=48):
            return "La solicitud debe realizarse al menos 48 horas antes"

    return None


def _can_manage(db, user: dict, refund: dict) -> bool:
    if user["rol"] == "administrador":
        return True
    ticket = db.boletas.find_one({"_id": refund["boletaId"]})
    if not ticket:
        return False
    event, _ = _find_event(db, ticket["funcionId"])
    organizer_id = event["organizadorId"]
    organizer = db.organizadores.find_one({"_id": organizer_id})
    if not organizer:
        return False
    return (
        user.get("organizadorId") == organizer_id
        or user["_id"] == organizer_id
        or user["_id"] == organizer.get("usuarioId")
    )


def _general_capacity(db, redis_cli, ticket: dict) -> int:
    capacity_key = f"cupo:{ticket['funcionId']}:{ticket['seccion']}"
    current = redis_cli.get(capacity_key)
    if current is not None:
        return int(current)

    _event, show = _find_event(db, ticket["funcionId"])
    venue = db.recintos.find_one({"_id": show["recintoId"]})
    section = next(
        (
            item
            for item in (venue or {}).get("secciones", [])
            if item.get("codigo") == ticket["seccion"]
        ),
        None,
    )
    if not section:
        return 0

    reserved = sum(
        int(item.get("cantidad", 0))
        for reservation in db.reservas.find({
            "funcionId": ticket["funcionId"],
            "estado": "activa",
        })
        for item in reservation.get("items", [])
        if item.get("seccion") == ticket["seccion"]
    )
    sold = db.boletas.count_documents({
        "funcionId": ticket["funcionId"],
        "seccion": ticket["seccion"],
        "estado": {"$in": ["valida", "usada"]},
    })
    available = max(int(section.get("capacidad", 0)) - reserved - sold, 0)
    redis_cli.set(capacity_key, available)
    return available


def create(db, redis_cli, user: dict, data: dict) -> dict:
    ticket = db.boletas.find_one({"_id": data["boletaId"]})
    if not ticket:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Boleta no encontrada")
    if ticket["compradorId"] != user["_id"] and user["rol"] != "administrador":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "La boleta pertenece a otro usuario",
        )
    if ticket["estado"] != "valida":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Solo pueden devolverse boletas válidas",
        )

    policy_error = _policy_allows(db, ticket)
    if policy_error:
        raise HTTPException(status.HTTP_409_CONFLICT, policy_error)

    if data["tipo"] == "cambio_funcion":
        if not data.get("nuevaFuncionId"):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Cambio de función requiere nuevaFuncionId",
            )
        _find_event(db, data["nuevaFuncionId"])

    existing = db.devoluciones.find_one({
        "boletaId": ticket["_id"],
        "estado": "pendiente",
    })
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La boleta ya tiene una solicitud pendiente",
        )

    refund = {
        "_id": f"dev_{uuid.uuid4().hex[:12]}",
        "ordenId": ticket["ordenId"],
        "boletaId": ticket["_id"],
        "compradorId": ticket["compradorId"],
        "tipo": data["tipo"],
        "motivo": data["motivo"],
        "nuevaFuncionId": data.get("nuevaFuncionId"),
        "monto": float(ticket["precio"]),
        "estado": "pendiente",
        "solicitadaEn": _iso(_now()),
    }
    db.devoluciones.insert_one(refund)
    return refund


def get(db, refund_id: str, user: dict) -> dict:
    refund = db.devoluciones.find_one({"_id": refund_id})
    if not refund:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Devolución no encontrada")
    if (
        user["rol"] not in ("administrador", "organizador")
        and refund["compradorId"] != user["_id"]
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "La devolución pertenece a otro usuario",
        )
    if user["rol"] == "organizador" and not _can_manage(db, user, refund):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No puede consultar devoluciones de otro organizador",
        )
    return refund


def approve(db, redis_cli, refund_id: str, user: dict) -> dict:
    refund = db.devoluciones.find_one({"_id": refund_id})
    if not refund:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Devolución no encontrada")
    if refund["estado"] != "pendiente":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La devolución ya fue procesada",
        )
    if user["rol"] not in ("administrador", "organizador"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede aprobar devoluciones")
    if not _can_manage(db, user, refund):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No puede aprobar devoluciones de otro organizador",
        )

    ticket = db.boletas.find_one({"_id": refund["boletaId"]})
    if not ticket or ticket["estado"] != "valida":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La boleta ya no está disponible",
        )

    updated_ticket = db.boletas.find_one_and_update(
        {"_id": ticket["_id"], "estado": "valida"},
        {"$set": {"estado": "devuelta", "devueltaEn": _iso(_now())}},
        return_document=True,
    )
    if not updated_ticket:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La boleta ya fue modificada",
        )

    if ticket.get("silla"):
        redis_cli.delete(
            f"lock:silla:{ticket['funcionId']}:{ticket['silla']}"
        )
    else:
        capacity_key = f"cupo:{ticket['funcionId']}:{ticket['seccion']}"
        _general_capacity(db, redis_cli, ticket)
        redis_cli.incrby(capacity_key, int(ticket.get("cantidad", 1)))

    updated_refund = db.devoluciones.find_one_and_update(
        {"_id": refund["_id"], "estado": "pendiente"},
        {
            "$set": {
                "estado": "aprobada",
                "procesadaEn": _iso(_now()),
                "procesadaPor": user["_id"],
            }
        },
        return_document=True,
    )
    db.ordenes.find_one_and_update(
        {"_id": refund["ordenId"]},
        {"$set": {"estado": "reembolsada"}},
    )

    if refund["tipo"] == "cambio_funcion":
        new_show_id = refund.get("nuevaFuncionId")
        if not new_show_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "La devolución no incluye nuevaFuncionId",
            )
        db.devoluciones.update_one(
            {"_id": refund["_id"]},
            {"$set": {"funcionOrigenId": ticket["funcionId"], "funcionDestinoId": new_show_id}},
        )
        if updated_refund:
            updated_refund["funcionOrigenId"] = ticket["funcionId"]
            updated_refund["funcionDestinoId"] = new_show_id

    return updated_refund or refund


def reject(db, refund_id: str, user: dict, motivo: str) -> dict:
    refund = db.devoluciones.find_one({"_id": refund_id})
    if not refund:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Devolución no encontrada")
    if refund["estado"] != "pendiente":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La devolución ya fue procesada",
        )
    if user["rol"] not in ("administrador", "organizador"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede rechazar devoluciones")
    if not _can_manage(db, user, refund):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No puede rechazar devoluciones de otro organizador",
        )

    updated = db.devoluciones.find_one_and_update(
        {"_id": refund["_id"], "estado": "pendiente"},
        {
            "$set": {
                "estado": "rechazada",
                "motivoRechazo": motivo,
                "procesadaEn": _iso(_now()),
                "procesadaPor": user["_id"],
            }
        },
        return_document=True,
    )
    return updated or refund
