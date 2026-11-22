import uuid


def _new_id() -> str:
    return f"ord_{uuid.uuid4().hex[:8]}"


def insert(db, data: dict) -> dict:
    data["_id"] = _new_id()
    db.ordenes.insert_one(data)
    return data


def find_by_id(db, order_id: str) -> dict | None:
    return db.ordenes.find_one({"_id": order_id})


def find_by_idempotency_key(db, idempotency_key: str) -> dict | None:
    return db.ordenes.find_one({"idempotencyKey": idempotency_key})


def find_by_buyer(db, buyer_id: str) -> list[dict]:
    return list(
        db.ordenes.find(
            {"compradorId": buyer_id},
            sort=[("fechaCreacion", -1)],
        )
    )
