import uuid


def _new_id() -> str:
    return f"bol_{uuid.uuid4().hex[:12]}"


def insert(db, data: dict) -> dict:
    data["_id"] = data.get("_id") or _new_id()
    db.boletas.insert_one(data)
    return data


def find_by_id(db, ticket_id: str) -> dict | None:
    return db.boletas.find_one({"_id": ticket_id})


def find_by_code(db, code: str) -> dict | None:
    return db.boletas.find_one({"codigo": code})


def find_by_order(db, order_id: str) -> list[dict]:
    return list(db.boletas.find({"ordenId": order_id}))


def find_by_buyer(db, buyer_id: str) -> list[dict]:
    return list(db.boletas.find({"compradorId": buyer_id}))


def mark_used(db, ticket_id: str, used_at: str) -> dict | None:
    return db.boletas.find_one_and_update(
        {"_id": ticket_id, "estado": "valida"},
        {"$set": {"estado": "usada", "usadaEn": used_at}},
        return_document=True,
    )
