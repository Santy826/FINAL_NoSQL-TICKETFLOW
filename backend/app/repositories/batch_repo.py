import uuid


def _new_batch_id() -> str:
    return f"lot_{uuid.uuid4().hex[:12]}"


def _new_invoice_id() -> str:
    return f"fac_{uuid.uuid4().hex[:12]}"


def insert(db, data: dict) -> dict:
    data["_id"] = _new_batch_id()
    db.lotes.insert_one(data)
    return data


def insert_invoice(db, data: dict) -> dict:
    data["_id"] = _new_invoice_id()
    db.facturas.insert_one(data)
    return data


def find_by_id(db, batch_id: str) -> dict | None:
    return db.lotes.find_one({"_id": batch_id})


def find_invoices(db) -> list[dict]:
    return list(db.facturas.find({}, sort=[("fechaEmision", -1)]))
