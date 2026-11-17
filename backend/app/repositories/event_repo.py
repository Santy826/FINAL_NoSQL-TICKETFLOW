import uuid


def _new_id() -> str:
    return f"evt_{uuid.uuid4().hex[:8]}"


def _new_funcion_id() -> str:
    return f"fn_{uuid.uuid4().hex[:6]}"


def insert(db, data: dict) -> dict:
    data["_id"] = _new_id()
    data["estado"] = "borrador"
    for func in data.get("funciones", []):
        if "funcionId" not in func:
            func["funcionId"] = _new_funcion_id()
    db.eventos.insert_one(data)
    return data


def find_all(db, filtros: dict | None = None) -> list[dict]:
    query = filtros or {}
    return list(db.eventos.find(query))


def find_by_id(db, event_id: str) -> dict | None:
    return db.eventos.find_one({"_id": event_id})


def find_by_organizer(db, organizer_id: str) -> list[dict]:
    return list(db.eventos.find({"organizadorId": organizer_id}))


def update(db, event_id: str, data: dict) -> dict | None:
    return db.eventos.find_one_and_update(
        {"_id": event_id},
        {"$set": data},
        return_document=True,
    )


def cancel(db, event_id: str) -> dict | None:
    return db.eventos.find_one_and_update(
        {"_id": event_id, "estado": {"$ne": "cancelado"}},
        {"$set": {"estado": "cancelado"}},
        return_document=True,
    )


def add_shows(db, event_id: str, funciones: list[dict]) -> dict | None:
    for func in funciones:
        if "funcionId" not in func:
            func["funcionId"] = _new_funcion_id()
    return db.eventos.find_one_and_update(
        {"_id": event_id},
        {"$push": {"funciones": {"$each": funciones}}},
        return_document=True,
    )
