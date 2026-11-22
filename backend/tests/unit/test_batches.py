import pytest
from fastapi import HTTPException

from app.services import batch_service


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
        result = [
            dict(doc)
            for doc in self.docs
            if all(self._match(doc, key, value) for key, value in (query or {}).items())
        ]
        sort = kwargs.get("sort")
        if sort:
            key, direction = sort[0]
            result.sort(key=lambda item: item.get(key, ""), reverse=direction < 0)
        return result

    def insert_one(self, doc):
        self.docs.append(dict(doc))
        return doc

    def find_one_and_update(self, query, update, return_document=False):
        for doc in self.docs:
            if all(self._match(doc, key, value) for key, value in query.items()):
                if "$set" in update:
                    doc.update(update["$set"])
                if "$push" in update:
                    key, value = next(iter(update["$push"].items()))
                    doc.setdefault(key, []).append(value)
                return dict(doc)
        return None

    def update_one(self, query, update):
        for doc in self.docs:
            if all(self._match(doc, key, value) for key, value in query.items()):
                if "$inc" in update:
                    path, amount = next(iter(update["$inc"].items()))
                    if path == "secciones.$.capacidad":
                        code_query = next(
                            (
                                key
                                for key in query
                                if key.startswith("secciones.")
                            ),
                            None,
                        )
                        code = query.get(code_query)
                        for section in doc.get("secciones", []):
                            if section["codigo"] == code:
                                section["capacidad"] += amount
                if "$push" in update:
                    key, value = next(iter(update["$push"].items()))
                    doc.setdefault(key, []).append(dict(value))
                if "$set" in update:
                    for key, value in update["$set"].items():
                        if "." in key:
                            continue
                        doc[key] = value
                return

    @staticmethod
    def _match(doc, key, value):
        if "." not in key:
            return doc.get(key) == value
        if key == "funciones.funcionId":
            return any(
                function.get("funcionId") == value
                for function in doc.get("funciones", [])
            )
        if key.startswith("secciones.") and key.endswith(".codigo"):
            return any(section.get("codigo") == value for section in doc.get("secciones", []))
        return True


class DB:
    def __init__(self):
        self.eventos = Collection([{
            "_id": "evt_01",
            "organizadorId": "org_01",
            "funciones": [{
                "funcionId": "fn_01",
                "recintoId": "rec_01",
                "ciudad": "Cali",
                "fechaHora": "2027-01-01T20:00:00-05:00",
                "precios": {"GENERAL": 70000},
            }],
        }])
        self.recintos = Collection([{
            "_id": "rec_01",
            "secciones": [{
                "codigo": "GENERAL",
                "tipo": "general",
                "capacidad": 100,
            }],
        }])
        self.organizadores = Collection([{
            "_id": "org_01",
            "comision": 10,
            "usuarioId": "usr_org",
        }])
        self.lotes = Collection()
        self.facturas = Collection()


def _admin():
    return {"_id": "usr_admin", "rol": "administrador"}


def test_ampliacion_actualiza_inventario_y_crea_factura():
    db = DB()
    redis = FakeRedis()
    result = batch_service.create(
        db,
        redis,
        _admin(),
        {
            "tipo": "ampliacion",
            "funcionId": "fn_01",
            "seccion": "GENERAL",
            "cantidad": 50,
            "precio": 80000,
        },
    )

    assert result["lote"]["tipo"] == "ampliacion"
    assert result["factura"]["subtotal"] == 4000000
    assert result["factura"]["comision"] == 400000
    assert result["factura"]["totalOrganizador"] == 3600000
    assert db.recintos.docs[0]["secciones"][0]["capacidad"] == 150
    assert redis.get("cupo:fn_01:GENERAL") == "150"


def test_nueva_seccion_actualiza_recinto_factura_y_redis():
    db = DB()
    redis = FakeRedis()
    result = batch_service.create(
        db,
        redis,
        _admin(),
        {
            "tipo": "nueva_seccion",
            "funcionId": "fn_01",
            "seccion": "VIP",
            "cantidad": 40,
            "precio": 120000,
        },
    )

    assert result["lote"]["seccion"] == "VIP"
    assert redis.get("cupo:fn_01:VIP") == "40"
    assert any(section["codigo"] == "VIP" for section in db.recintos.docs[0]["secciones"])
    assert len(db.facturas.docs) == 1


def test_nueva_funcion_crea_funcion_e_inventario():
    db = DB()
    redis = FakeRedis()
    result = batch_service.create(
        db,
        redis,
        _admin(),
        {
            "tipo": "nueva_funcion",
            "eventId": "evt_01",
            "seccion": "GENERAL",
            "cantidad": 200,
            "precio": 90000,
        },
    )

    assert result["lote"]["tipo"] == "nueva_funcion"
    assert len(db.eventos.docs[0]["funciones"]) == 2
    assert result["lote"]["funcionId"].startswith("fn_")
    assert redis.get(f"cupo:{result['lote']['funcionId']}:GENERAL") == "200"


def test_seccion_invalida_rechaza_lote():
    db = DB()
    redis = FakeRedis()

    with pytest.raises(HTTPException) as error:
        batch_service.create(
            db,
            redis,
            _admin(),
            {
                "tipo": "ampliacion",
                "funcionId": "fn_01",
                "seccion": "NO_EXISTE",
                "cantidad": 10,
                "precio": 80000,
            },
        )

    assert error.value.status_code == 422
    assert len(db.lotes.docs) == 0
