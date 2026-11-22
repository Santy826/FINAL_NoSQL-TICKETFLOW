import uuid


def _new_id() -> str:
    return f"dev_{uuid.uuid4().hex[:12]}"


def insert(db, data: dict) -> dict:
    data["_id"] = _new_id()
    db.devoluciones.insert_one(data)
    return data


def find_by_id(db, refund_id: str) -> dict | None:
    return db.devoluciones.find_one({"_id": refund_id})
