import uuid


def _new_id() -> str:
    return f"rec_{uuid.uuid4().hex[:8]}"


def insert(db, data: dict) -> dict:
    data["_id"] = _new_id()
    db.recintos.insert_one(data)
    return data


def find_all(db, filtros: dict | None = None) -> list[dict]:
    query = filtros or {}
    return list(db.recintos.find(query))


def find_by_id(db, venue_id: str) -> dict | None:
    return db.recintos.find_one({"_id": venue_id})


def update(db, venue_id: str, data: dict) -> dict | None:
    return db.recintos.find_one_and_update(
        {"_id": venue_id},
        {"$set": data},
        return_document=True,
    )


def delete(db, venue_id: str) -> bool:
    result = db.recintos.delete_one({"_id": venue_id})
    return result.deleted_count > 0
