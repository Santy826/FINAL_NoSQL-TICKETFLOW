from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from app.repositories import venue_repo

RESERVATION_TTL_SECONDS = 600

_GENERAL_DECR_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 0 then
  redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[3])
end
local remaining = redis.call('DECRBY', KEYS[1], ARGV[2])
if remaining < 0 then
  redis.call('INCRBY', KEYS[1], ARGV[2])
  return -1
end
return remaining
"""

_GENERAL_RESTORE_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 0 then
  redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[3])
  return tonumber(ARGV[1])
end
local remaining = redis.call('INCRBY', KEYS[1], ARGV[2])
if remaining > tonumber(ARGV[1]) then
  remaining = tonumber(ARGV[1])
  redis.call('SET', KEYS[1], remaining, 'EX', ARGV[3])
end
return remaining
"""


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _find_show(db, funcion_id: str) -> tuple[dict, dict]:
    event = db.eventos.find_one({"funciones.funcionId": funcion_id})
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Función no encontrada")
    show = next(
        (item for item in event.get("funciones", []) if item.get("funcionId") == funcion_id),
        None,
    )
    if not show:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Función no encontrada")
    return event, show


def _venue_for_show(db, show: dict) -> dict:
    venue = venue_repo.find_by_id(db, show["recintoId"])
    if not venue:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recinto de la función no encontrado")
    return venue


def _seat_ids(section: dict) -> list[str]:
    code = section["codigo"]
    if section.get("tipo") == "numerada":
        return [
            f"{code}-{row['fila']}-{number}"
            for row in section.get("filas", [])
            for number in range(1, row["sillas"] + 1)
        ]
    if section.get("tipo") == "mesa":
        return [f"{code}-{table['mesa']}" for table in section.get("mesas", [])]
    return []


def _active_reservations(db, funcion_id: str) -> list[dict]:
    now = _iso(_now())
    return list(
        db.reservas.find(
            {
                "funcionId": funcion_id,
                "estado": "activa",
                "expiraEn": {"$gt": now},
            }
        )
    )


def _reserved_seats(db, funcion_id: str) -> set[str]:
    seats: set[str] = set()
    for reservation in _active_reservations(db, funcion_id):
        for item in reservation.get("items", []):
            if item.get("silla"):
                seats.add(item["silla"])
    return seats


def _sold_seats(db, funcion_id: str) -> set[str]:
    seats: set[str] = set()
    for ticket in db.boletas.find({"funcionId": funcion_id, "estado": {"$in": ["valida", "usada"]}}):
        if ticket.get("silla"):
            seats.add(ticket["silla"])
    return seats


def _section_snapshot(db, funcion_id: str, section: dict, redis_cli=None) -> dict:
    reserved = _reserved_seats(db, funcion_id)
    sold = _sold_seats(db, funcion_id)
    seats = _seat_ids(section)
    if seats:
        states = [
            {
                "silla": seat,
                "estado": (
                    "vendida"
                    if seat in sold
                    else "reservada"
                    if seat in reserved or (
                        redis_cli is not None
                        and redis_cli.get(f"lock:silla:{funcion_id}:{seat}")
                    )
                    else "libre"
                ),
            }
            for seat in seats
        ]
        return {
            "seccion": section["codigo"],
            "tipo": section.get("tipo"),
            "capacidad": len(seats),
            "disponibles": sum(item["estado"] == "libre" for item in states),
            "reservadas": sum(item["estado"] == "reservada" for item in states),
            "vendidas": sum(item["estado"] == "vendida" for item in states),
            "sillas": states,
        }

    capacity = int(section.get("capacidad", 0))
    reserved_count = sum(
        item.get("cantidad", 0)
        for reservation in _active_reservations(db, funcion_id)
        for item in reservation.get("items", [])
        if item.get("seccion") == section["codigo"]
    )
    sold_count = db.boletas.count_documents(
        {
            "funcionId": funcion_id,
            "seccion": section["codigo"],
            "estado": {"$in": ["valida", "usada"]},
        }
    )
    mongo_available = max(capacity - reserved_count - sold_count, 0)
    redis_available = mongo_available
    if redis_cli is not None:
        redis_remaining = redis_cli.get(f"cupo:{funcion_id}:{section['codigo']}")
        if redis_remaining is not None:
            redis_available = max(int(redis_remaining), 0)
    return {
        "seccion": section["codigo"],
        "tipo": section.get("tipo"),
        "capacidad": capacity,
        "disponibles": redis_available,
        "reservadas": reserved_count,
        "vendidas": sold_count,
    }


def availability(db, funcion_id: str, redis_cli=None) -> dict:
    _, show = _find_show(db, funcion_id)
    venue = _venue_for_show(db, show)
    sections = [_section_snapshot(db, funcion_id, section, redis_cli) for section in venue.get("secciones", [])]
    return {"funcionId": funcion_id, "secciones": sections}


def seats(db, funcion_id: str, redis_cli=None) -> dict:
    data = availability(db, funcion_id, redis_cli)
    return {
        "funcionId": funcion_id,
        "sillas": [
            seat
            for section in data["secciones"]
            for seat in section.get("sillas", [])
        ],
        "zonasGenerales": [
            {
                "seccion": section["seccion"],
                "disponibles": section["disponibles"],
                "capacidad": section["capacidad"],
            }
            for section in data["secciones"]
            if section["tipo"] == "general"
        ],
    }


def _validate_items(db, funcion_id: str, items: list[dict]) -> None:
    _, show = _find_show(db, funcion_id)
    venue = _venue_for_show(db, show)
    sections = {section["codigo"]: section for section in venue.get("secciones", [])}
    for item in items:
        section = sections.get(item["seccion"])
        if not section:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Sección no válida")
        if section.get("tipo") == "general":
            if item.get("silla"):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Una zona general no tiene silla")
            continue
        if item.get("cantidad", 1) != 1 or not item.get("silla"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Debe indicar una silla individual")
        if item["silla"] not in _seat_ids(section):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Silla no válida")


def create(db, redis_cli, user_id: str, funcion_id: str, items: list[dict]) -> dict:
    _validate_items(db, funcion_id, items)
    requested_seats = [item["silla"] for item in items if item.get("silla")]
    if len(requested_seats) != len(set(requested_seats)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Sillas repetidas")

    reserved_seats = _reserved_seats(db, funcion_id)
    sold_seats = _sold_seats(db, funcion_id)
    unavailable = set(requested_seats) & (reserved_seats | sold_seats)
    if unavailable:
        seat = min(unavailable)
        raise HTTPException(status.HTTP_409_CONFLICT, f"La silla {seat} no está disponible")

    reservation_id = f"res_{uuid.uuid4().hex[:8]}"
    acquired: list[tuple[str, str, int]] = []
    try:
        for seat in requested_seats:
            key = f"lock:silla:{funcion_id}:{seat}"
            if not redis_cli.set(key, reservation_id, nx=True, ex=RESERVATION_TTL_SECONDS):
                raise HTTPException(status.HTTP_409_CONFLICT, f"La silla {seat} no está disponible")
            acquired.append(("lock", key, 0))

        for item in items:
            if item.get("silla"):
                continue
            key = f"cupo:{funcion_id}:{item['seccion']}"
            _, show = _find_show(db, funcion_id)
            section = next(
                section
                for section in _venue_for_show(db, show).get("secciones", [])
                if section["codigo"] == item["seccion"]
            )
            snapshot = _section_snapshot(db, funcion_id, section)
            remaining = redis_cli.eval(
                _GENERAL_DECR_SCRIPT,
                1,
                key,
                snapshot["disponibles"],
                item["cantidad"],
                RESERVATION_TTL_SECONDS,
            )
            if remaining == -1:
                raise HTTPException(status.HTTP_409_CONFLICT, "Cupo insuficiente")
            acquired.append(("capacity", key, item["cantidad"]))

        created = _now()
        reservation = {
            "_id": reservation_id,
            "funcionId": funcion_id,
            "usuarioId": user_id,
            "items": items,
            "estado": "activa",
            "creadaEn": _iso(created),
            "expiraEn": _iso(created + timedelta(seconds=RESERVATION_TTL_SECONDS)),
        }
        db.reservas.insert_one(reservation)
        redis_cli.set(
            f"reserva:{reservation_id}",
            json.dumps(reservation),
            ex=RESERVATION_TTL_SECONDS,
        )
        return reservation
    except Exception:
        for kind, key, amount in acquired:
            if kind == "capacity":
                redis_cli.incrby(key, amount)
            else:
                redis_cli.delete(key)
        raise


def _release_reservation(db, redis_cli, reservation: dict) -> None:
    for item in reservation.get("items", []):
        key_suffix = item.get("seccion")
        if item.get("silla"):
            lock_key = f"lock:silla:{reservation['funcionId']}:{item['silla']}"
            if redis_cli.get(lock_key) == reservation["_id"]:
                redis_cli.delete(lock_key)
        else:
            key = f"cupo:{reservation['funcionId']}:{key_suffix}"
            _, show = _find_show(db, reservation["funcionId"])
            section = next(
                section
                for section in _venue_for_show(db, show).get("secciones", [])
                if section["codigo"] == key_suffix
            )
            snapshot = _section_snapshot(db, reservation["funcionId"], section)
            redis_cli.eval(
                _GENERAL_RESTORE_SCRIPT,
                1,
                key,
                snapshot["disponibles"],
                item["cantidad"],
                RESERVATION_TTL_SECONDS,
            )
    redis_cli.delete(f"reserva:{reservation['_id']}")


def get(db, redis_cli, reservation_id: str, user_id: str) -> dict:
    reservation = db.reservas.find_one({"_id": reservation_id, "usuarioId": user_id})
    if not reservation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reserva no encontrada")
    if reservation["estado"] == "activa" and reservation["expiraEn"] <= _iso(_now()):
        updated = db.reservas.find_one_and_update(
            {"_id": reservation_id, "estado": "activa"},
            {"$set": {"estado": "expirada"}},
            return_document=True,
        )
        if updated:
            _release_reservation(db, redis_cli, updated)
        reservation["estado"] = "expirada"
    return reservation


def cancel(db, redis_cli, reservation_id: str, user_id: str) -> dict:
    reservation = db.reservas.find_one({"_id": reservation_id, "usuarioId": user_id})
    if not reservation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reserva no encontrada")
    if reservation["estado"] != "activa":
        raise HTTPException(status.HTTP_409_CONFLICT, "La reserva ya no está activa")
    if reservation["expiraEn"] <= _iso(_now()):
        updated = db.reservas.find_one_and_update(
            {"_id": reservation_id, "estado": "activa"},
            {"$set": {"estado": "expirada"}},
            return_document=True,
        )
        if updated:
            _release_reservation(db, redis_cli, updated)
        raise HTTPException(status.HTTP_409_CONFLICT, "La reserva ya expiró")

    updated = db.reservas.find_one_and_update(
        {"_id": reservation_id, "estado": "activa"},
        {"$set": {"estado": "cancelada"}},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status.HTTP_409_CONFLICT, "La reserva ya no está activa")
    _release_reservation(db, redis_cli, updated)
    return updated


def expire_active_reservations(db, redis_cli) -> int:
    now = _iso(_now())
    expired = list(db.reservas.find({"estado": "activa", "expiraEn": {"$lte": now}}))
    count = 0
    for reservation in expired:
        updated = db.reservas.find_one_and_update(
            {"_id": reservation["_id"], "estado": "activa"},
            {"$set": {"estado": "expirada"}},
            return_document=True,
        )
        if updated:
            _release_reservation(db, redis_cli, updated)
            count += 1
    return count
