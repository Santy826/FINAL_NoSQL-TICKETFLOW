from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.repositories import order_repo


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _age(user: dict, purchase_date: datetime) -> int | None:
    birth = user.get("fechaNacimiento")
    if not birth:
        return None
    if isinstance(birth, date):
        birth_date = birth
    else:
        try:
            birth_date = date.fromisoformat(str(birth))
        except ValueError:
            return None
    today = purchase_date.date()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


def _find_event(db, funcion_id: str) -> tuple[dict, dict]:
    event = db.eventos.find_one({"funciones.funcionId": funcion_id})
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Función no encontrada")
    show = next(
        (
            item
            for item in event.get("funciones", [])
            if item.get("funcionId") == funcion_id
        ),
        None,
    )
    if not show:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Función no encontrada")
    return event, show


def _build_items(db, funcion_id: str, reservation_items: list[dict]) -> tuple[list[dict], float]:
    _, show = _find_event(db, funcion_id)
    prices = show.get("precios", {})
    items: list[dict] = []
    subtotal = 0.0

    for reservation_item in reservation_items:
        section = reservation_item.get("seccion")
        quantity = int(reservation_item.get("cantidad", 1))
        if section not in prices:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"No existe precio para la sección {section}",
            )
        unit_price = float(prices[section])
        item_subtotal = unit_price * quantity
        items.append({
            "seccion": section,
            "silla": reservation_item.get("silla"),
            "cantidad": quantity,
            "precioUnitario": unit_price,
            "subtotal": item_subtotal,
        })
        subtotal += item_subtotal

    return items, subtotal


def pay(db, redis_cli, user: dict, data: dict) -> tuple[dict, bool]:
    key = data["idempotencyKey"].strip()
    reservation_id = data["reservaId"].strip()
    if not key:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "La clave de idempotencia es obligatoria",
        )

    existing = order_repo.find_by_idempotency_key(db, key)
    if existing:
        if existing.get("reservaId") != reservation_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "La clave de idempotencia ya fue usada con otra reserva",
            )
        reservation = db.reservas.find_one({"_id": reservation_id})
        if reservation:
            from app.services import ticket_service

            ticket_service.emit_tickets(db, redis_cli, existing, reservation)
        redis_cli.set(
            f"idem:{key}",
            existing["_id"],
            ex=settings.IDEMPOTENCY_TTL_SECONDS,
        )
        return existing, False

    redis_key = f"idem:{key}"
    acquired = redis_cli.set(
        redis_key,
        "processing",
        nx=True,
        ex=settings.IDEMPOTENCY_TTL_SECONDS,
    )
    if not acquired:
        existing_id = redis_cli.get(redis_key)
        if existing_id and existing_id != "processing":
            existing = order_repo.find_by_id(db, existing_id)
            if existing:
                if existing.get("reservaId") != reservation_id:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        "La clave de idempotencia ya fue usada con otra reserva",
                    )
                reservation = db.reservas.find_one({"_id": reservation_id})
                if reservation:
                    from app.services import ticket_service

                    ticket_service.emit_tickets(db, redis_cli, existing, reservation)
                return existing, False
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El pago con esta clave está siendo procesado",
        )

    try:
        reservation = db.reservas.find_one({"_id": reservation_id})
        if not reservation:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Reserva no encontrada")
        if reservation.get("usuarioId") != user["_id"]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "La reserva pertenece a otro usuario",
            )
        if reservation.get("estado") != "activa":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "La reserva ya no está activa",
            )
        if _parse_iso(reservation["expiraEn"]) <= _now():
            raise HTTPException(status.HTTP_409_CONFLICT, "La reserva ya expiró")

        funcion_id = reservation["funcionId"]
        event, _show = _find_event(db, funcion_id)
        items, subtotal = _build_items(db, funcion_id, reservation.get("items", []))
        purchase_date = _now()
        paid_reservation = db.reservas.find_one_and_update(
            {"_id": reservation_id, "estado": "activa"},
            {"$set": {"estado": "pagada", "pagadaEn": _iso(purchase_date)}},
            return_document=True,
        )
        if not paid_reservation:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "La reserva ya no está disponible para pago",
            )

        order = {
            "idempotencyKey": key,
            "reservaId": reservation_id,
            "compradorId": user["_id"],
            "funcionId": funcion_id,
            "organizadorId": event["organizadorId"],
            "categoria": event.get("categoria", ""),
            "edadComprador": _age(user, purchase_date),
            "items": items,
            "subtotal": subtotal,
            "estado": "pagada",
            "metodoPago": data["metodoPago"],
            "fechaCreacion": _iso(purchase_date),
        }
        try:
            created = order_repo.insert(db, order)
        except DuplicateKeyError:
            existing = order_repo.find_by_idempotency_key(db, key)
            if not existing:
                raise
            if existing.get("reservaId") != reservation_id:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "La clave de idempotencia ya fue usada con otra reserva",
                )
            from app.services import ticket_service

            ticket_service.emit_tickets(db, redis_cli, existing, paid_reservation)
            redis_cli.set(
                redis_key,
                existing["_id"],
                ex=settings.IDEMPOTENCY_TTL_SECONDS,
            )
            return existing, False

        from app.services import ticket_service

        ticket_service.emit_tickets(db, redis_cli, created, paid_reservation)
        redis_cli.set(
            redis_key,
            created["_id"],
            ex=settings.IDEMPOTENCY_TTL_SECONDS,
        )
        return created, True
    except HTTPException:
        if redis_cli.get(redis_key) == "processing":
            redis_cli.delete(redis_key)
        raise
    except Exception:
        if redis_cli.get(redis_key) == "processing":
            redis_cli.delete(redis_key)
        raise


def get(db, order_id: str, user: dict) -> dict:
    order = order_repo.find_by_id(db, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Orden no encontrada")
    if user["rol"] not in ("administrador",) and order["compradorId"] != user["_id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La orden pertenece a otro usuario")
    return order


def get_for_user(db, buyer_id: str, user: dict) -> list[dict]:
    if user["rol"] != "administrador" and user["_id"] != buyer_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No puede consultar las órdenes de otro usuario",
        )
    return order_repo.find_by_buyer(db, buyer_id)
