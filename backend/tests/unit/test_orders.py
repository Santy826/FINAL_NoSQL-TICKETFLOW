from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.services import order_service


class FakeRedis:
    def __init__(self):
        self.values = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = str(value)
        return True

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.values.pop(key, None)


class Collection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def find_one(self, query=None, *args, **kwargs):
        for doc in self.docs:
            if all(self._match(doc, key, value) for key, value in (query or {}).items()):
                return dict(doc)
        return None

    def find(self, query=None, *args, **kwargs):
        result = [
            dict(doc)
            for doc in self.docs
            if all(self._match(doc, key, value) for key, value in (query or {}).items())
        ]
        return sorted(
            result,
            key=lambda item: item.get("fechaCreacion", ""),
            reverse=True,
        )

    def insert_one(self, doc):
        self.docs.append(dict(doc))

    def find_one_and_update(self, query, update, return_document=False):
        for doc in self.docs:
            if all(self._match(doc, key, value) for key, value in query.items()):
                doc.update(update["$set"])
                return dict(doc)
        return None

    @staticmethod
    def _match(doc, key, value):
        if "." not in key:
            return doc.get(key) == value
        if key == "funciones.funcionId":
            return any(
                function.get("funcionId") == value
                for function in doc.get("funciones", [])
            )
        return True


class DB:
    def __init__(self):
        self.reservas = Collection()
        self.ordenes = Collection()
        self.boletas = Collection()
        self.validaciones = Collection()
        self.eventos = Collection([{
            "_id": "evt_01",
            "organizadorId": "org_01",
            "categoria": "musica",
            "funciones": [{
                "funcionId": "fn_01",
                "precios": {
                    "NORTE": 250000,
                    "GENERAL": 80000,
                },
            }],
        }])
        self.usuarios = Collection()


@pytest.fixture
def order_db():
    db = DB()
    db.reservas.docs = [{
        "_id": "res_01",
        "usuarioId": "usr_01",
        "funcionId": "fn_01",
        "estado": "activa",
        "expiraEn": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
        "items": [
            {"seccion": "NORTE", "silla": "NORTE-A-1", "cantidad": 1},
        ],
    }]
    return db


def _user():
    return {
        "_id": "usr_01",
        "nombre": "Comprador",
        "correo": "buyer@test.com",
        "fechaNacimiento": "2000-01-01",
        "rol": "comprador",
    }


def test_pago_exitoso_es_idempotente(order_db):
    redis = FakeRedis()
    data = {
        "reservaId": "res_01",
        "idempotencyKey": "payment-001",
        "metodoPago": "simulado",
    }

    order, created = order_service.pay(order_db, redis, _user(), data)
    repeated, repeated_created = order_service.pay(order_db, redis, _user(), data)

    assert created is True
    assert repeated_created is False
    assert repeated["_id"] == order["_id"]
    assert len(order_db.ordenes.docs) == 1
    assert redis.get("idem:payment-001") == order["_id"]
    assert order_db.reservas.docs[0]["estado"] == "pagada"
    assert order["subtotal"] == 250000


def test_misma_clave_con_otra_reserva_es_rechazada(order_db):
    redis = FakeRedis()
    order_db.reservas.docs.append({
        "_id": "res_02",
        "usuarioId": "usr_01",
        "funcionId": "fn_01",
        "estado": "activa",
        "expiraEn": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
        "items": [{"seccion": "GENERAL", "cantidad": 1}],
    })
    first = {
        "reservaId": "res_01",
        "idempotencyKey": "payment-002",
        "metodoPago": "simulado",
    }
    order_service.pay(order_db, redis, _user(), first)

    second = dict(first, reservaId="res_02")
    with pytest.raises(HTTPException) as error:
        order_service.pay(order_db, redis, _user(), second)

    assert error.value.status_code == 409


def test_reserva_de_otro_usuario_es_rechazada(order_db):
    redis = FakeRedis()
    data = {
        "reservaId": "res_01",
        "idempotencyKey": "payment-003",
        "metodoPago": "simulado",
    }
    other_user = dict(_user(), _id="usr_02")

    with pytest.raises(HTTPException) as error:
        order_service.pay(order_db, redis, other_user, data)

    assert error.value.status_code == 403
    assert len(order_db.ordenes.docs) == 0


def test_reserva_expirada_es_rechazada(order_db):
    redis = FakeRedis()
    order_db.reservas.docs[0]["expiraEn"] = "2000-01-01T00:00:00+00:00"
    data = {
        "reservaId": "res_01",
        "idempotencyKey": "payment-004",
        "metodoPago": "simulado",
    }

    with pytest.raises(HTTPException) as error:
        order_service.pay(order_db, redis, _user(), data)

    assert error.value.status_code == 409
    assert len(order_db.ordenes.docs) == 0
