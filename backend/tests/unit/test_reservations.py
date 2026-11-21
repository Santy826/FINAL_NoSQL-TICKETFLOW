from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException

from app.services import reservation_service


class FakeRedis:
    def __init__(self):
        self.values = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = str(value)
        return True

    def delete(self, key):
        self.values.pop(key, None)

    def get(self, key):
        return self.values.get(key)

    def decrby(self, key, amount):
        return int(self.values.setdefault(key, 0)) - amount

    def incrby(self, key, amount):
        value = int(self.values.get(key, 0)) + amount
        self.values[key] = str(value)
        return value

    def eval(self, script, numkeys, key, seed, amount, ttl):
        if key not in self.values:
            self.values[key] = str(seed)
        remaining = int(self.values[key]) - amount
        if remaining < 0:
            return -1
        self.values[key] = str(remaining)
        return remaining


@pytest.fixture
def reservation_db():
    class Collection:
        def __init__(self):
            self.docs = []

        def find_one(self, query=None, *args, **kwargs):
            for doc in self.docs:
                matches = all(doc.get(key) == value for key, value in (query or {}).items())
                if matches:
                    return dict(doc)
            return None

        def find(self, *args, **kwargs):
            return list(self.docs)

        def insert_one(self, doc):
            self.docs.append(dict(doc))

        def find_one_and_update(self, query, update, return_document=False):
            for doc in self.docs:
                if doc.get("_id") == query.get("_id") and doc.get("estado") == query.get("estado"):
                    doc.update(update["$set"])
                    return dict(doc)
            return None

        def count_documents(self, *args, **kwargs):
            return 0

    class DB:
        def __init__(self):
            self.eventos = Collection()
            self.recintos = Collection()
            self.reservas = Collection()
            self.boletas = Collection()

    db = DB()
    db.recintos.docs = [{
        "_id": "rec_01",
        "secciones": [{
            "codigo": "NORTE",
            "tipo": "numerada",
            "filas": [{"fila": "A", "sillas": 10}],
        }, {
            "codigo": "GENERAL",
            "tipo": "general",
            "capacidad": 100,
        }],
    }]
    db.eventos.docs = [{
        "_id": "evt_01",
        "funciones": [{"funcionId": "fn_01", "recintoId": "rec_01"}],
    }]

    def find_event(query):
        if "funciones.funcionId" in query:
            return db.eventos.docs[0]
        return None

    db.eventos.find_one = find_event

    def find_venue(query):
        venue_id = query.get("_id") if isinstance(query, dict) else query
        return db.recintos.docs[0] if db.recintos.docs[0]["_id"] == venue_id else None

    db.recintos.find_one = find_venue
    return db


def test_reserva_numerada_exitosa_y_cancelacion(reservation_db):
    redis_cli = FakeRedis()
    reservation = reservation_service.create(
        reservation_db,
        redis_cli,
        "usr_01",
        "fn_01",
        [{"seccion": "NORTE", "silla": "NORTE-A-1", "cantidad": 1}],
    )

    assert reservation["estado"] == "activa"
    assert redis_cli.get("lock:silla:fn_01:NORTE-A-1") == reservation["_id"]

    cancelled = reservation_service.cancel(
        reservation_db, redis_cli, reservation["_id"], "usr_01"
    )
    assert cancelled["estado"] == "cancelada"
    assert redis_cli.get("lock:silla:fn_01:NORTE-A-1") is None


def test_reserva_misma_silla_rechazada(reservation_db):
    redis_cli = FakeRedis()
    items = [{"seccion": "NORTE", "silla": "NORTE-A-1", "cantidad": 1}]
    reservation_service.create(reservation_db, redis_cli, "usr_01", "fn_01", items)

    with pytest.raises(HTTPException) as error:
        reservation_service.create(reservation_db, redis_cli, "usr_02", "fn_01", items)

    assert error.value.status_code == 409


def test_concurrencia_misma_silla_solo_un_exito(reservation_db):
    redis_cli = FakeRedis()
    items = [{"seccion": "NORTE", "silla": "NORTE-A-2", "cantidad": 1}]

    def reserve(index):
        try:
            reservation_service.create(
                reservation_db, redis_cli, f"usr_{index}", "fn_01", items
            )
            return 201
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(reserve, range(20)))

    assert results.count(201) == 1
    assert results.count(409) == 19


def test_disponibilidad_incluye_bloqueo_redis_y_cupo_general(reservation_db):
    redis_cli = FakeRedis()
    redis_cli.set("lock:silla:fn_01:NORTE-A-3", "res_external", nx=True)
    redis_cli.set("cupo:fn_01:GENERAL", 91)

    data = reservation_service.availability(reservation_db, "fn_01", redis_cli)

    norte = next(section for section in data["secciones"] if section["seccion"] == "NORTE")
    locked = next(seat for seat in norte["sillas"] if seat["silla"] == "NORTE-A-3")
    general = next(section for section in data["secciones"] if section["seccion"] == "GENERAL")

    assert locked["estado"] == "reservada"
    assert general["disponibles"] == 91


def test_reserva_expirada_no_puede_cancelarse(reservation_db):
    redis_cli = FakeRedis()
    reservation = reservation_service.create(
        reservation_db,
        redis_cli,
        "usr_01",
        "fn_01",
        [{"seccion": "NORTE", "silla": "NORTE-A-4", "cantidad": 1}],
    )
    for doc in reservation_db.reservas.docs:
        if doc["_id"] == reservation["_id"]:
            doc["expiraEn"] = "2000-01-01T00:00:00+00:00"

    with pytest.raises(HTTPException) as error:
        reservation_service.cancel(
            reservation_db, redis_cli, reservation["_id"], "usr_01"
        )

    assert error.value.status_code == 409
    assert reservation_db.reservas.find_one({"_id": reservation["_id"]})["estado"] == "expirada"


def test_zona_general_atomica_y_silla_invalida(reservation_db):
    redis_cli = FakeRedis()
    general = reservation_service.create(
        reservation_db,
        redis_cli,
        "usr_01",
        "fn_01",
        [{"seccion": "GENERAL", "cantidad": 3}],
    )
    assert general["estado"] == "activa"
    assert redis_cli.get("cupo:fn_01:GENERAL") == "97"

    with pytest.raises(HTTPException) as error:
        reservation_service.create(
            reservation_db,
            redis_cli,
            "usr_02",
            "fn_01",
            [{"seccion": "NORTE", "silla": "NORTE-A-999", "cantidad": 1}],
        )
    assert error.value.status_code == 422
