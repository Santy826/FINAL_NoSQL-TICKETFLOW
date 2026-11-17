import uuid


def _new_id() -> str:
    return f"usr_{uuid.uuid4().hex[:8]}"


def insert(db, data: dict) -> dict:
    data["_id"] = _new_id()
    db.usuarios.insert_one(data)
    return data


def find_by_email(db, correo: str) -> dict | None:
    return db.usuarios.find_one({"correo": correo})


def find_by_id(db, user_id: str) -> dict | None:
    return db.usuarios.find_one({"_id": user_id})
