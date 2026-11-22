import pytest
from fastapi import HTTPException

from app.services import refund_service


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

    def incrby(self, key, amount):
        value = int(self.values.get(key, 0)) + amount
        self.values[key] = str(value)
        return value


class Collection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def find_one(self, query=None, *args, **kwargs):
        for doc in self.docs:
            if all(self._match(doc, key, value) for key, value in (query or {}).items()):
                return dict(doc)
        return None

    def find(self, query=None, *args, **kwargs):
        return [
            dict(doc)
            for doc in self.docs
            if all(doc.get(key) == value for key, value in (query or {}).items())
        ]

    def insert_one(self, doc):
        self.docs.append(dict(doc))
        return doc

    def find_one_and_update(self, query, update, return_document=False):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                doc.update(update["$set"])
                return dict(doc)
        return None

    def update_one(self, query, update):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                doc.update(update["$set"])

    @staticmethod
    def _match(doc, key, value):
        if key == "funciones.funcionId":
            return any(
                function.get("funcionId") == value
                for function in doc.get("funciones", [])
            )
        return doc.get(key) == value


class DB:
    def __init__(self, policy="hasta_48h_antes"):
        self.eventos = Collection([{
            "_id": "evt_01",
            "organizadorId": "org_01",
            "funciones": [{
                "funcionId": "fn_01",
                "fechaHora": "2027-06-01T20:00:00-05:00",
            }],
        }])
        self.organizadores = Collection([{
            "_id": "org_01",
            "politicaDevolucion": policy,
            "usuarioId": "usr_org",
        }])
        self.boletas = Collection([{
            "_id": "bol_01",
            "codigo": "bol_01.signature",
            "ordenId": "ord_01",
            "compradorId": "usr_01",
            "funcionId": "fn_01",
            "seccion": "GENERAL",
            "silla": None,
            "cantidad": 2,
            "precio": 80000,
            "estado": "valida",
        }])
        self.ordenes = Collection([{
            "_id": "ord_01",
            "estado": "pagada",
        }])
        self.devoluciones = Collection()


def _buyer():
    return {"_id": "usr_01", "rol": "comprador"}


def _admin():
    return {"_id": "usr_admin", "rol": "administrador"}


def test_solicitud_aprobada_libera_cupo_y_reembolsa_orden():
    db = DB()
    redis = FakeRedis()
    redis.set("cupo:fn_01:GENERAL", 98)
    refund = refund_service.create(
        db,
        redis,
        _buyer(),
        {
            "boletaId": "bol_01",
            "tipo": "reembolso",
            "motivo": "No puedo asistir",
        },
    )

    approved = refund_service.approve(db, redis, refund["_id"], _admin())

    assert approved["estado"] == "aprobada"
    assert db.boletas.docs[0]["estado"] == "devuelta"
    assert db.ordenes.docs[0]["estado"] == "reembolsada"
    assert redis.get("cupo:fn_01:GENERAL") == "100"


def test_solicitud_rechazada_no_libera_cupo():
    db = DB()
    redis = FakeRedis()
    redis.set("cupo:fn_01:GENERAL", 98)
    refund = refund_service.create(
        db,
        redis,
        _buyer(),
        {
            "boletaId": "bol_01",
            "tipo": "reembolso",
            "motivo": "Cambio de planes",
        },
    )

    rejected = refund_service.reject(
        db,
        refund["_id"],
        _admin(),
        "Solicitud rechazada",
    )

    assert rejected["estado"] == "rechazada"
    assert db.boletas.docs[0]["estado"] == "valida"
    assert redis.get("cupo:fn_01:GENERAL") == "98"


def test_politica_sin_devolucion_rechaza_solicitud():
    db = DB(policy="sin_devolucion")
    redis = FakeRedis()

    with pytest.raises(HTTPException) as error:
        refund_service.create(
            db,
            redis,
            _buyer(),
            {
                "boletaId": "bol_01",
                "tipo": "reembolso",
                "motivo": "No puedo asistir",
            },
        )

    assert error.value.status_code == 409


def test_boleta_usada_no_puede_solicitar_devolucion():
    db = DB()
    db.boletas.docs[0]["estado"] = "usada"

    with pytest.raises(HTTPException) as error:
        refund_service.create(
            db,
            FakeRedis(),
            _buyer(),
            {
                "boletaId": "bol_01",
                "tipo": "reembolso",
                "motivo": "No puedo asistir",
            },
        )

    assert error.value.status_code == 409


def test_solicitud_duplicada_es_rechazada():
    db = DB()
    redis = FakeRedis()
    data = {
        "boletaId": "bol_01",
        "tipo": "reembolso",
        "motivo": "No puedo asistir",
    }
    refund_service.create(db, redis, _buyer(), data)

    with pytest.raises(HTTPException) as error:
        refund_service.create(db, redis, _buyer(), data)

    assert error.value.status_code == 409
