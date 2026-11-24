from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.repositories import batch_repo


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _find_event_by_show(db, funcion_id: str) -> tuple[dict, dict]:
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


def _find_event(db, event_id: str) -> dict:
    event = db.eventos.find_one({"_id": event_id})
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento no encontrado")
    return event


def _find_organizer(db, organizer_id: str) -> dict:
    organizer = db.organizadores.find_one({"_id": organizer_id})
    if not organizer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organizador no encontrado")
    return organizer


def _validate_owner(db, user: dict, organizer_id: str) -> None:
    if user["rol"] == "administrador":
        return
    organizer = db.organizadores.find_one({"_id": organizer_id})
    if not organizer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organizador no encontrado")
    if (
        user.get("organizadorId") != organizer_id
        and user["_id"] != organizer_id
        and user["_id"] != organizer.get("usuarioId")
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No puede crear lotes para otro organizador",
        )


def create(db, redis_cli, user: dict, data: dict) -> dict:
    batch_type = data["tipo"]
    cantidad = data["cantidad"]
    precio = float(data["precio"])
    created_at = _iso(_now())

    if batch_type == "nueva_funcion":
        event_id = data.get("eventId")
        if not event_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "nueva_funcion requiere eventId",
            )
        event = _find_event(db, event_id)
        funcion_id = f"fn_{uuid.uuid4().hex[:8]}"
        venue_id = event["funciones"][0]["recintoId"] if event.get("funciones") else None
        if not venue_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "El evento no tiene una función base para definir el recinto",
            )
        base_show = event["funciones"][0]
        new_show = {
            "funcionId": funcion_id,
            "fechaHora": base_show["fechaHora"],
            "recintoId": venue_id,
            "ciudad": base_show["ciudad"],
            "estado": "abierta",
            "precios": {data["seccion"]: precio},
        }
        updated = db.eventos.find_one_and_update(
            {"_id": event_id},
            {"$push": {"funciones": new_show}},
            return_document=True,
        )
        if not updated:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento no encontrado")
        organizer_id = event["organizadorId"]
        section = data.get("seccion")
        if not section:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "nueva_funcion requiere seccion",
            )
        venue = db.recintos.find_one({"_id": venue_id})
        if not venue or not any(
            item.get("codigo") == section
            for item in venue.get("secciones", [])
        ):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "La sección no pertenece al recinto",
            )
        _validate_owner(db, user, organizer_id)
        if section:
            redis_cli.set(f"cupo:{funcion_id}:{section}", cantidad)
    else:
        funcion_id = data.get("funcionId")
        if not funcion_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "El lote requiere funcionId",
            )
        event, show = _find_event_by_show(db, funcion_id)
        organizer_id = event["organizadorId"]
        _validate_owner(db, user, organizer_id)
        section = data.get("seccion")

        venue = db.recintos.find_one({"_id": show["recintoId"]})
        if not venue:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Recinto no encontrado")

        if batch_type == "nueva_seccion":
            if not section:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "nueva_seccion requiere seccion",
                )
            existing = next(
                (
                    item
                    for item in venue.get("secciones", [])
                    if item.get("codigo") == section
                ),
                None,
            )
            if not existing:
                venue_section = {
                    "codigo": section,
                    "tipo": "general",
                    "capacidad": cantidad,
                }
                db.recintos.update_one(
                    {"_id": venue["_id"]},
                    {"$push": {"secciones": venue_section}},
                )
            else:
                if existing.get("tipo") != "general":
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "La sección existente no es una zona general",
                    )
                db.recintos.update_one(
                    {
                        "_id": venue["_id"],
                        "secciones.codigo": section,
                        "secciones.tipo": "general",
                    },
                    {"$inc": {"secciones.$.capacidad": cantidad}},
                )

        elif batch_type in ("preventa", "ampliacion"):
            if not section:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "El lote requiere seccion",
                )
            section_doc = next(
                (
                    item
                    for item in venue.get("secciones", [])
                    if item.get("codigo") == section
                ),
                None,
            )
            if not section_doc:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "La sección no pertenece al recinto",
                )
            if section_doc.get("tipo") != "general":
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "preventa y ampliacion solo aplican a zonas generales",
                )
            if batch_type in ("preventa", "ampliacion"):
                db.recintos.update_one(
                    {
                        "_id": venue["_id"],
                        "secciones.codigo": section,
                        "secciones.tipo": "general",
                    },
                    {"$inc": {"secciones.$.capacidad": cantidad}},
                )

        updated_prices = dict(show.get("precios", {}))
        if section:
            updated_prices[section] = precio
        db.eventos.update_one(
            {
                "_id": event["_id"],
                "funciones.funcionId": funcion_id,
            },
            {"$set": {"funciones.$.precios": updated_prices}},
        )
        redis_key = f"cupo:{funcion_id}:{section}" if section else None
        if redis_key and batch_type in (
            "preventa",
            "ampliacion",
            "nueva_seccion",
        ):
            current = redis_cli.get(redis_key)
            venue_section = next(
                (
                    item
                    for item in venue.get("secciones", [])
                    if item.get("codigo") == section
                ),
                None,
            )
            base_capacity = (
                int(venue_section.get("capacidad", 0))
                if venue_section
                else 0
            )
            if current is None:
                updated_venue = db.recintos.find_one({"_id": venue["_id"]})
                updated_section = next(
                    (
                        item
                        for item in (updated_venue or {}).get("secciones", [])
                        if item.get("codigo") == section
                    ),
                    None,
                )
                if updated_section:
                    redis_cli.set(
                        redis_key,
                        int(updated_section.get("capacidad", base_capacity)),
                    )
                else:
                    redis_cli.set(redis_key, base_capacity)
            else:
                redis_cli.incrby(redis_key, cantidad)

    organizer = _find_organizer(db, organizer_id)
    commission = float(organizer.get("comision", 0))
    subtotal = precio * cantidad
    commission_amount = subtotal * commission / 100
    invoice_total = subtotal - commission_amount

    batch = {
        "tipo": batch_type,
        "funcionId": funcion_id,
        "eventId": data.get("eventId"),
        "organizadorId": organizer_id,
        "seccion": section,
        "cantidad": cantidad,
        "precio": precio,
        "estado": "activo",
        "creadoPor": user["_id"],
        "creadoEn": created_at,
    }
    created_batch = batch_repo.insert(db, batch)

    invoice = {
        "loteId": created_batch["_id"],
        "organizadorId": organizer_id,
        "subtotal": subtotal,
        "comisionPorcentaje": commission,
        "comision": commission_amount,
        "totalOrganizador": invoice_total,
        "estado": "emitida",
        "fechaEmision": created_at,
    }
    created_invoice = batch_repo.insert_invoice(db, invoice)

    try:
        from app.services.report_service import invalidate
        invalidate(db, redis_cli)
    except Exception:
        pass

    return {
        "lote": created_batch,
        "factura": created_invoice,
    }


def list_invoices(db, user: dict) -> list[dict]:
    invoices = batch_repo.find_invoices(db)
    if user["rol"] == "administrador":
        return invoices
    organizer_id = user.get("organizadorId")
    if not organizer_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El usuario no está asociado a un organizador",
        )
    return [
        invoice
        for invoice in invoices
        if invoice["organizadorId"] == organizer_id
    ]
