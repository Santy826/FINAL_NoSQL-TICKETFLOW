from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import HTTPException, status


REPORT_CACHE_TTL_SECONDS = 300
EVENT_CACHE_TTL_SECONDS = 300


def _cache_key(name: str, filters: dict) -> str:
    clean = {key: str(value) for key, value in sorted(filters.items()) if value not in (None, "")}
    return f"report:{name}:{urlencode(clean)}"


def execute(db, redis_cli, name: str, filters: dict, pipeline: list[dict]) -> tuple[list | dict, str]:
    key = _cache_key(name, filters)
    try:
        cached = redis_cli.get(key)
    except Exception:
        cached = None
    if cached:
        try:
            return json.loads(cached), "hit"
        except json.JSONDecodeError:
            pass

    try:
        collection = getattr(db, name_to_collection(name))
        result = list(collection.aggregate(pipeline))
    except AttributeError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Base de datos no disponible",
        )

    try:
        redis_cli.set(key, json.dumps(result, default=str), ex=REPORT_CACHE_TTL_SECONDS)
    except Exception:
        pass
    return result, "miss"


def name_to_collection(name: str) -> str:
    collections = {
        "occupancy": "boletas",
        "inventory-value": "eventos",
        "sales": "ordenes",
        "organizers": "organizadores",
        "show-availability": "eventos",
        "buyers-by-age": "ordenes",
        "top-seats": "boletas",
        "sales-by-type": "ordenes",
        "revenue": "ordenes",
        "low-sales": "eventos",
        "refunds": "devoluciones",
        "fraud-attempts": "validaciones",
        "attendance": "boletas",
    }
    return collections[name]


def invalidate(db, redis_cli, pattern: str = "report:*") -> int:
    try:
        patterns = [pattern]
        if pattern == "report:*":
            patterns = ["report:*", "event:*"]
        keys = []
        for current_pattern in patterns:
            keys.extend(list(redis_cli.scan_iter(match=current_pattern)))
        keys = list(dict.fromkeys(keys))
        if keys:
            redis_cli.delete(*keys)
        return len(keys)
    except Exception:
        return 0


def _parse_iso(value) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def _seat_ids(section: dict) -> list[str]:
    code = section["codigo"]
    if section.get("tipo") == "numerada":
        return [
            f"{code}-{row['fila']}-{number}"
            for row in section.get("filas", [])
            for number in range(1, int(row.get("sillas", 0)) + 1)
        ]
    if section.get("tipo") == "mesa":
        return [
            f"{code}-{table['mesa']}"
            for table in section.get("mesas", [])
        ]
    return []


def _section_capacity(section: dict) -> int:
    seats = _seat_ids(section)
    if seats:
        if section.get("tipo") == "numerada":
            return len(seats)
        if section.get("tipo") == "mesa":
            return sum(int(table.get("capacidad", 0)) for table in section.get("mesas", []))
    return int(section.get("capacidad", 0))


def _cached_compute(db, redis_cli, name: str, filters: dict, compute):
    key = _cache_key(name, filters)
    try:
        cached = redis_cli.get(key)
    except Exception:
        cached = None
    if cached:
        try:
            return json.loads(cached), "hit"
        except json.JSONDecodeError:
            pass
    result = compute()
    try:
        redis_cli.set(key, json.dumps(result, default=str), ex=REPORT_CACHE_TTL_SECONDS)
    except Exception:
        pass
    return result, "miss"


def get_cached_events(db, redis_cli, filters: dict | None = None):
    clean_filters = filters or {}
    key = f"event:list:{urlencode(dict(sorted(clean_filters.items())))}"
    try:
        cached = redis_cli.get(key)
    except Exception:
        cached = None
    if cached:
        try:
            return json.loads(cached), "hit"
        except json.JSONDecodeError:
            pass
    result = list(db.eventos.find(clean_filters))
    try:
        redis_cli.set(key, json.dumps(result, default=str), ex=EVENT_CACHE_TTL_SECONDS)
    except Exception:
        pass
    return result, "miss"


def _find_show(db, funcion_id: str) -> tuple[dict, dict] | tuple[None, None]:
    event = db.eventos.find_one({"funciones.funcionId": funcion_id})
    if not event:
        return None, None
    show = next(
        (item for item in event.get("funciones", []) if item.get("funcionId") == funcion_id),
        None,
    )
    return event, show


def _active_reservations(db, funcion_id: str) -> list[dict]:
    now = datetime.now(UTC)
    reservations = []
    for reservation in db.reservas.find({"funcionId": funcion_id, "estado": "activa"}):
        expira = _parse_iso(reservation.get("expiraEn"))
        if expira is None or expira > now:
            reservations.append(reservation)
    return reservations


def _section_usage(db, funcion_id: str, section: dict) -> dict:
    codigo = section["codigo"]
    seats = _seat_ids(section)
    sold_tickets = list(db.boletas.find({
        "funcionId": funcion_id,
        "seccion": codigo,
        "estado": {"$in": ["valida", "usada"]},
    }))

    sold_seat_ids = {
        ticket["silla"]
        for ticket in sold_tickets
        if isinstance(ticket.get("silla"), str) and ticket["silla"]
    }
    sold_general = sum(
        int(ticket.get("cantidad", 1))
        for ticket in sold_tickets
        if not ticket.get("silla")
    )

    reserved_seat_ids = set()
    reserved_general = 0
    for reservation in _active_reservations(db, funcion_id):
        for item in reservation.get("items", []):
            if item.get("seccion") != codigo:
                continue
            if item.get("silla"):
                reserved_seat_ids.add(item["silla"])
            else:
                reserved_general += int(item.get("cantidad", 1))

    if seats:
        if section.get("tipo") == "mesa":
            sold_ids = sold_seat_ids & set(seats)
            reserved_ids = (reserved_seat_ids & set(seats)) - sold_seat_ids
            table_capacity = {
                f"{codigo}-{table['mesa']}": int(table.get("capacidad", 0))
                for table in section.get("mesas", [])
            }
            sold = sum(table_capacity.get(seat_id, 0) for seat_id in sold_ids)
            reserved = sum(table_capacity.get(seat_id, 0) for seat_id in reserved_ids)
        else:
            sold = len(sold_seat_ids & set(seats))
            reserved = len((reserved_seat_ids & set(seats)) - sold_seat_ids)
        capacity = _section_capacity(section)
        available = max(capacity - sold - reserved, 0)
    else:
        capacity = _section_capacity(section)
        sold = sold_general
        reserved = reserved_general
        available = max(capacity - sold - reserved, 0)

    occupied = sold + reserved
    porcentaje = round((occupied / capacity * 100), 2) if capacity else 0.0
    return {
        "seccion": codigo,
        "tipo": section.get("tipo"),
        "capacidad": capacity,
        "vendidas": sold,
        "reservadas": reserved,
        "ocupadas": occupied,
        "disponibles": available,
        "ocupacionPorcentaje": porcentaje,
    }


def occupancy(db, redis_cli, funcion_id: str | None = None, seccion: str | None = None) -> tuple[list, str]:
    def compute():
        function_ids = [funcion_id] if funcion_id else []
        if not funcion_id:
            function_ids = [
                show.get("funcionId")
                for event in db.eventos.find({})
                for show in event.get("funciones", [])
                if show.get("funcionId")
            ]
        result = []
        for current_function_id in dict.fromkeys(function_ids):
            _event, show = _find_show(db, current_function_id)
            if not show:
                continue
            venue = db.recintos.find_one({"_id": show.get("recintoId")})
            if not venue:
                continue
            for section in venue.get("secciones", []):
                if seccion and section.get("codigo") != seccion:
                    continue
                usage = _section_usage(db, current_function_id, section)
                usage["funcionId"] = current_function_id
                result.append(usage)
        return result

    return _cached_compute(
        db,
        redis_cli,
        "occupancy",
        {"funcionId": funcion_id, "seccion": seccion},
        compute,
    )


def inventory_value(db, redis_cli, funcion_id: str | None = None) -> tuple[list, str]:
    def compute():
        function_ids = [funcion_id] if funcion_id else []
        if not funcion_id:
            function_ids = [
                show.get("funcionId")
                for event in db.eventos.find({})
                for show in event.get("funciones", [])
                if show.get("funcionId")
            ]
        result = []
        for current_function_id in dict.fromkeys(function_ids):
            _event, show = _find_show(db, current_function_id)
            if not show:
                continue
            venue = db.recintos.find_one({"_id": show.get("recintoId")})
            if not venue:
                continue
            prices = show.get("precios", {})
            for section in venue.get("secciones", []):
                codigo = section["codigo"]
                usage = _section_usage(db, current_function_id, section)
                price = float(prices.get(codigo, 0))
                result.append({
                    "funcionId": current_function_id,
                    "seccion": codigo,
                    "tipo": section.get("tipo"),
                    "precio": price,
                    "vendidas": usage["vendidas"],
                    "reservadas": usage["reservadas"],
                    "disponibles": usage["disponibles"],
                    "valorInventario": price * usage["disponibles"],
                })
        return result

    return _cached_compute(
        db,
        redis_cli,
        "inventory-value",
        {"funcionId": funcion_id},
        compute,
    )


def sales(db, redis_cli, desde: str | None = None, hasta: str | None = None, evento_id: str | None = None) -> tuple[list, str]:
    match: dict = {"estado": {"$ne": "reembolsada"}}
    if desde or hasta:
        match["fechaCreacion"] = {}
        if desde:
            match["fechaCreacion"]["$gte"] = desde
        if hasta:
            match["fechaCreacion"]["$lte"] = hasta
    pipeline = [
        {"$match": match},
        {"$unwind": "$items"},
        {"$group": {
            "_id": {"$substrBytes": ["$fechaCreacion", 0, 10]},
            "ordenes": {"$addToSet": "$_id"},
            "boletas": {"$sum": {"$ifNull": ["$items.cantidad", 1]}},
            "ingresos": {"$sum": "$items.subtotal"},
        }},
        {"$project": {
            "_id": 1,
            "ordenes": {"$size": "$ordenes"},
            "boletas": 1,
            "ingresos": 1,
        }},
        {"$sort": {"_id": 1}},
    ]
    if evento_id:
        pipeline.insert(0, {"$match": {"funcionId": evento_id}})
    return execute(db, redis_cli, "sales", {"desde": desde, "hasta": hasta, "eventoId": evento_id}, pipeline)


def organizers(db, redis_cli) -> tuple[list, str]:
    pipeline = [
        {"$lookup": {
            "from": "eventos",
            "localField": "_id",
            "foreignField": "organizadorId",
            "as": "eventos",
        }},
        {"$project": {
            "_id": 1,
            "razonSocial": 1,
            "nit": 1,
            "comision": 1,
            "eventos": {
                "$map": {
                    "input": "$eventos",
                    "as": "evento",
                    "in": {"id": "$$evento._id", "nombre": "$$evento.nombre", "estado": "$$evento.estado"},
                },
            },
        }},
    ]
    return execute(db, redis_cli, "organizers", {}, pipeline)


def show_availability(db, redis_cli, evento_id: str | None = None) -> tuple[list, str]:
    def compute():
        events = (
            [db.eventos.find_one({"_id": evento_id})]
            if evento_id
            else get_cached_events(db, redis_cli)[0]
        )
        result = []
        for event in events:
            if not event:
                continue
            for show in event.get("funciones", []):
                funcion_id = show.get("funcionId")
                venue = db.recintos.find_one({"_id": show.get("recintoId")})
                if not venue:
                    continue
                sections = [
                    _section_usage(db, funcion_id, section)
                    for section in venue.get("secciones", [])
                ]
                capacity = sum(section["capacidad"] for section in sections)
                sold = sum(section["vendidas"] for section in sections)
                reserved = sum(section["reservadas"] for section in sections)
                available = sum(section["disponibles"] for section in sections)
                occupied = sold + reserved
                result.append({
                    "eventoId": event["_id"],
                    "nombreEvento": event.get("nombre"),
                    "funcionId": funcion_id,
                    "ciudad": show.get("ciudad"),
                    "fechaHora": show.get("fechaHora"),
                    "recinto": venue.get("nombre"),
                    "capacidad": capacity,
                    "vendidas": sold,
                    "reservadas": reserved,
                    "ocupadas": occupied,
                    "disponibles": available,
                    "ocupacionPorcentaje": round(occupied / capacity * 100, 2) if capacity else 0.0,
                    "secciones": sections,
                })
        return result

    return _cached_compute(
        db,
        redis_cli,
        "show-availability",
        {"eventoId": evento_id},
        compute,
    )


def buyers_by_age(db, redis_cli, desde: str | None = None, hasta: str | None = None, evento_id: str | None = None) -> tuple[list, str]:
    match: dict = {"edadComprador": {"$ne": None}}
    if desde:
        match["fechaCreacion"] = {"$gte": desde}
    if hasta:
        match.setdefault("fechaCreacion", {})["$lte"] = hasta
    if evento_id:
        match["funcionId"] = evento_id
    pipeline = [
        {"$match": match},
        {"$sort": {"fechaCreacion": -1}},
        {"$group": {
            "_id": "$compradorId",
            "edad": {"$first": "$edadComprador"},
            "ingresos": {"$sum": "$subtotal"},
        }},
        {"$bucket": {
            "groupBy": "$edad",
            "boundaries": [0, 18, 26, 36, 51, 200],
            "default": "otro",
            "output": {
                "compradores": {"$sum": 1},
                "ingresos": {"$sum": "$ingresos"},
            },
        }},
    ]
    result = execute(db, redis_cli, "buyers-by-age", {"desde": desde, "hasta": hasta, "eventoId": evento_id}, pipeline)
    data, status = result
    labels = ["menores de 18", "18 a 25", "26 a 35", "36 a 50", "mas de 50"]
    buckets = {row["_id"]: row for row in data if "_id" in row}
    converted = []
    boundaries = [0, 18, 26, 36]
    for index, boundary in enumerate(boundaries):
        row = buckets.get(boundary, {})
        converted.append({
            "rango": labels[index],
            "compradores": row.get("compradores", 0),
            "ingresos": row.get("ingresos", 0),
        })
    over50_rows = [
        buckets.get(51, {}),
        buckets.get(200, {}),
        buckets.get("otro", {}),
    ]
    converted.append({
        "rango": "mas de 50",
        "compradores": sum(row.get("compradores", 0) for row in over50_rows),
        "ingresos": sum(row.get("ingresos", 0) for row in over50_rows),
    })
    return converted, status


def top_seats(db, redis_cli, limite: int = 10) -> tuple[list, str]:
    limite = min(max(limite, 1), 100)
    pipeline = [
        {"$match": {"estado": {"$in": ["valida", "usada"]}}},
        {"$match": {"silla": {"$type": "string", "$ne": ""}}},
        {"$group": {"_id": {"seccion": "$seccion", "silla": "$silla"}, "ventas": {"$sum": 1}}},
        {"$sort": {"ventas": -1}},
        {"$limit": limite},
    ]
    return execute(db, redis_cli, "top-seats", {"limite": limite}, pipeline)


def sales_by_event_type(db, redis_cli) -> tuple[list, str]:
    pipeline = [
        {"$unwind": "$items"},
        {"$group": {
            "_id": {"categoria": "$categoria", "edad": "$edadComprador"},
            "boletas": {"$sum": {"$ifNull": ["$items.cantidad", 1]}},
            "ingresos": {"$sum": "$items.subtotal"},
        }},
        {"$group": {
            "_id": "$_id.categoria",
            "boletas": {"$sum": "$boletas"},
            "ingresos": {"$sum": "$ingresos"},
            "porEdad": {"$push": {
                "edadComprador": "$_id.edad",
                "boletas": "$boletas",
                "ingresos": "$ingresos",
            }},
        }},
        {"$sort": {"ingresos": -1}},
    ]
    return execute(db, redis_cli, "sales-by-type", {}, pipeline)


def revenue(db, redis_cli) -> tuple[list, str]:
    pipeline = [
        {"$match": {"estado": {"$in": ["pagada", "reembolsada"]}}},
        {"$lookup": {
            "from": "devoluciones",
            "localField": "_id",
            "foreignField": "ordenId",
            "as": "devoluciones",
        }},
        {"$set": {
            "devolucionesAprobadas": {
                "$filter": {
                    "input": "$devoluciones",
                    "as": "devolucion",
                    "cond": {"$eq": ["$$devolucion.estado", "aprobada"]},
                },
            },
        }},
        {"$project": {
            "organizadorId": 1,
            "subtotal": 1,
            "devolucionMonto": {"$sum": "$devolucionesAprobadas.monto"},
        }},
        {"$group": {
            "_id": "$organizadorId",
            "ventasBrutas": {"$sum": "$subtotal"},
            "reembolsos": {"$sum": "$devolucionMonto"},
        }},
        {"$lookup": {
            "from": "organizadores",
            "localField": "_id",
            "foreignField": "_id",
            "as": "organizador",
        }},
        {"$project": {
            "_id": 1,
            "ventasBrutas": 1,
            "reembolsos": 1,
            "ingresoNeto": {"$subtract": ["$ventasBrutas", "$reembolsos"]},
            "organizador": {"$arrayElemAt": ["$organizador", 0]},
        }},
    ]
    return execute(db, redis_cli, "revenue", {}, pipeline)


def low_sales(db, redis_cli, dias: int = 15) -> tuple[list, str]:
    dias = min(max(dias, 1), 365)
    def compute():
        now = datetime.now(UTC)
        limit = now + timedelta(days=dias)
        result = []
        events, _cache_status = get_cached_events(db, redis_cli, {"estado": {"$ne": "cancelado"}})
        for event in events:
            for show in event.get("funciones", []):
                if show.get("estado") in ("cancelada", "cancelado"):
                    continue
                show_date = _parse_iso(show.get("fechaHora"))
                if show_date is None or show_date < now or show_date > limit:
                    continue
                funcion_id = show.get("funcionId")
                venue = db.recintos.find_one({"_id": show.get("recintoId")})
                if not venue:
                    continue
                sections = [
                    _section_usage(db, funcion_id, section)
                    for section in venue.get("secciones", [])
                ]
                capacity = sum(section["capacidad"] for section in sections)
                sold = sum(section["vendidas"] for section in sections)
                reserved = sum(section["reservadas"] for section in sections)
                available = sum(section["disponibles"] for section in sections)
                occupied = sold + reserved
                porcentaje = round(occupied / capacity * 100, 2) if capacity else 0.0
                if porcentaje < 30:
                    result.append({
                        "eventoId": event["_id"],
                        "nombre": event.get("nombre"),
                        "funcionId": funcion_id,
                        "fechaHora": show.get("fechaHora"),
                        "capacidad": capacity,
                        "vendidas": sold,
                        "reservadas": reserved,
                        "disponibles": available,
                        "ocupacionPorcentaje": porcentaje,
                    })
        result.sort(key=lambda item: (item["ocupacionPorcentaje"], item["fechaHora"] or ""))
        return result

    return _cached_compute(
        db,
        redis_cli,
        "low-sales",
        {"dias": dias},
        compute,
    )


def refunds(db, redis_cli, desde: str | None = None, hasta: str | None = None) -> tuple[list, str]:
    match: dict = {}
    if desde or hasta:
        date_match = {}
        if desde:
            date_match["$gte"] = desde
        if hasta:
            date_match["$lte"] = hasta
        match["$or"] = [
            {"procesadaEn": date_match},
            {"solicitadaEn": date_match},
        ]
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$estado",
            "cantidad": {"$sum": 1},
            "monto": {"$sum": "$monto"},
        }},
        {"$sort": {"cantidad": -1}},
    ]
    return execute(db, redis_cli, "refunds", {"desde": desde, "hasta": hasta}, pipeline)


def fraud_attempts(db, redis_cli) -> tuple[list, str]:
    pipeline = [
        {"$match": {"resultado": {
            "$in": [
                "firma_invalida",
                "validacion_concurrente",
                "ya_usada",
                "boleta_devuelta",
                "boleta_anulada",
                "boleta_no_encontrada",
            ],
        }}},
        {"$lookup": {
            "from": "boletas",
            "localField": "boletaId",
            "foreignField": "_id",
            "as": "boleta",
        }},
        {"$set": {"boletaInfo": {"$arrayElemAt": ["$boleta", 0]}}},
        {"$lookup": {
            "from": "eventos",
            "let": {"funcionId": "$boletaInfo.funcionId"},
            "pipeline": [
                {"$match": {"$expr": {"$in": ["$$funcionId", "$funciones.funcionId"]}}},
                {"$project": {"_id": 1, "nombre": 1}},
            ],
            "as": "evento",
        }},
        {"$set": {"eventoInfo": {"$arrayElemAt": ["$evento", 0]}}},
        {"$group": {
            "_id": {
                "eventoId": "$eventoInfo._id",
                "evento": "$eventoInfo.nombre",
                "puerta": "$puerta",
                "resultado": "$resultado",
            },
            "intentos": {"$sum": 1},
        }},
        {"$sort": {"intentos": -1}},
    ]
    return execute(db, redis_cli, "fraud-attempts", {}, pipeline)


def attendance(db, redis_cli, funcion_id: str | None = None) -> tuple[list, str]:
    match: dict = {}
    if funcion_id:
        match["funcionId"] = funcion_id
    pipeline = [
        {"$match": match},
        {"$lookup": {
            "from": "validaciones",
            "let": {"boletaId": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {
                    "$and": [
                        {"$eq": ["$boletaId", "$$boletaId"]},
                        {"$eq": ["$resultado", "aceptada"]},
                    ],
                }}},
            ],
            "as": "validacionesAceptadas",
        }},
        {"$facet": {
            "porFuncion": [
                {"$group": {
                    "_id": "$funcionId",
                    "vendidas": {"$sum": {"$cond": [{"$in": ["$estado", ["valida", "usada"]]}, 1, 0]}},
                    "asistentes": {"$sum": {"$cond": [{"$gt": [{"$size": "$validacionesAceptadas"}, 0]}, 1, 0]}},
                }},
                {"$project": {
                    "_id": 0,
                    "funcionId": "$_id",
                    "vendidas": 1,
                    "asistentes": 1,
                    "inasistentes": {"$subtract": ["$vendidas", "$asistentes"]},
                }},
            ],
            "porPuerta": [
                {"$unwind": "$validacionesAceptadas"},
                {"$group": {
                    "_id": {
                        "funcionId": "$funcionId",
                        "puerta": "$validacionesAceptadas.puerta",
                        "franja": {"$substrBytes": ["$validacionesAceptadas.fecha", 11, 2]},
                    },
                    "asistentes": {"$sum": 1},
                }},
                {"$project": {
                    "_id": 0,
                    "funcionId": "$_id.funcionId",
                    "puerta": "$_id.puerta",
                    "asistentes": 1,
                    "franjaHoraria": "$_id.franja",
                }},
            ],
        }},
    ]
    return execute(db, redis_cli, "attendance", {"funcionId": funcion_id}, pipeline)
