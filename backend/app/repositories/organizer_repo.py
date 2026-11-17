import uuid


def _new_id() -> str:
    return f"org_{uuid.uuid4().hex[:8]}"


def insert(db, data: dict) -> dict:
    data["_id"] = _new_id()
    db.organizadores.insert_one(data)
    return data


def find_all(db) -> list[dict]:
    return list(db.organizadores.find())


def find_by_id(db, org_id: str) -> dict | None:
    return db.organizadores.find_one({"_id": org_id})


def find_by_nit(db, nit: str) -> dict | None:
    return db.organizadores.find_one({"nit": nit})


def update(db, org_id: str, data: dict) -> dict | None:
    return db.organizadores.find_one_and_update(
        {"_id": org_id},
        {"$set": data},
        return_document=True,
    )


def delete(db, org_id: str) -> bool:
    result = db.organizadores.delete_one({"_id": org_id})
    return result.deleted_count > 0
