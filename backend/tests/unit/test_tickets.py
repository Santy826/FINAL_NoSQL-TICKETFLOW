from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException

from app.services import ticket_service


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
            if all(
                (
                    any(
                        funcion.get("funcionId") == value
                        for funcion in doc.get("funciones", [])
                    )
                    if key == "funciones.funcionId"
                    else doc.get(key) == value
                )
                for key, value in (query or {}).items()
            ):
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


class DB:
    def __init__(self):
        self.boletas = Collection()
        self.validaciones = Collection()


def _order(items):
    return {
        "_id": "ord_test",
        "compradorId": "usr_buyer",
        "funcionId": "fn_test",
        "items": items,
        "fechaCreacion": "2026-11-22T12:00:00+00:00",
    }


def _reservation():
    return {
        "_id": "res_test",
        "items": [],
    }


def _validator():
    return {
        "_id": "usr_validator",
        "rol": "validador",
    }


def test_mis_boletas_resuelve_evento_nombre_fecha_y_recinto():
    db = DB()
    db.eventos = Collection([{
        "_id": "evt_rock",
        "nombre": "Concierto Rock",
        "categoria": "musica",
        "funciones": [{
            "funcionId": "fn_rock",
            "fechaHora": "2027-02-14T19:00:00-05:00",
            "recintoId": "rec_estadio",
            "ciudad": "Cali",
        }],
    }])
    db.recintos = Collection([{
        "_id": "rec_estadio",
        "nombre": "Estadio Principal",
        "ciudad": "Cali",
    }])
    db.boletas.docs.append({
        "_id": "bol_rock",
        "compradorId": "usr_buyer",
        "funcionId": "fn_rock",
        "seccion": "NORTE",
        "silla": "NORTE-1-1",
        "estado": "valida",
    })

    result = ticket_service.get_by_buyer(
        db,
        "usr_buyer",
        {"_id": "usr_buyer", "rol": "comprador"},
    )

    assert len(result) == 1
    assert result[0]["eventoId"] == "evt_rock"
    assert result[0]["eventoNombre"] == "Concierto Rock"
    assert result[0]["eventoFechaHora"] == "2027-02-14T19:00:00-05:00"
    assert result[0]["recintoNombre"] == "Estadio Principal"


def test_mis_boletas_informa_evento_no_disponible_sin_relacion():
    db = DB()
    db.eventos = Collection([])
    db.recintos = Collection([])
    db.boletas.docs.append({
        "_id": "bol_antigua",
        "compradorId": "usr_buyer",
        "funcionId": "fn_inexistente",
        "estado": "valida",
    })

    result = ticket_service.get_by_buyer(
        db,
        "usr_buyer",
        {"_id": "usr_buyer", "rol": "comprador"},
    )

    assert result[0]["eventoDisponible"] is False
    assert result[0]["eventoNombre"] is None


def test_emision_silla_genera_codigo_firmado_y_qr():
    db = DB()
    redis = FakeRedis()
    order = _order([{
        "seccion": "NORTE",
        "silla": "NORTE-A-1",
        "cantidad": 1,
        "precioUnitario": 250000,
        "subtotal": 250000,
    }])

    tickets = ticket_service.emit_tickets(db, redis, order, _reservation())

    assert len(tickets) == 1
    ticket = tickets[0]
    assert ticket["estado"] == "valida"
    assert ticket["silla"] == "NORTE-A-1"
    assert ticket["codigo"].startswith(ticket["_id"] + ".")
    assert ticket["qr"]
    assert ticket["firma"] == ticket_service._sign(ticket["_id"])


def test_emision_general_genera_una_boleta_por_cupo():
    db = DB()
    redis = FakeRedis()
    order = _order([{
        "seccion": "GENERAL",
        "silla": None,
        "cantidad": 3,
        "precioUnitario": 80000,
        "subtotal": 240000,
    }])

    tickets = ticket_service.emit_tickets(db, redis, order, _reservation())

    assert len(tickets) == 3
    assert all(ticket["silla"] is None for ticket in tickets)
    assert len({ticket["_id"] for ticket in tickets}) == 3
    assert len(ticket_service.emit_tickets(db, redis, order, _reservation())) == 3


def test_codigo_alterado_rechaza_y_registra_intento():
    db = DB()
    redis = FakeRedis()
    ticket = {
        "_id": "bol_altered",
        "codigo": "bol_altered." + ticket_service._sign("bol_altered"),
        "firma": ticket_service._sign("bol_altered"),
        "estado": "valida",
    }
    db.boletas.docs.append(ticket)

    with pytest.raises(HTTPException) as error:
        ticket_service.validate(
            db,
            redis,
            _validator(),
            {"codigo": "bol_altered.firma-alterada", "puerta": "Norte"},
        )

    assert error.value.status_code == 422
    assert db.validaciones.docs[0]["resultado"] == "firma_invalida"


def test_segundo_uso_rechaza_y_primer_uso_acepta():
    db = DB()
    redis = FakeRedis()
    ticket_id = "bol_used"
    code = ticket_id + "." + ticket_service._sign(ticket_id)
    db.boletas.docs.append({
        "_id": ticket_id,
        "codigo": code,
        "firma": ticket_service._sign(ticket_id),
        "estado": "valida",
    })
    data = {"codigo": code, "puerta": "Sur"}

    first = ticket_service.validate(db, redis, _validator(), data)

    assert first["resultado"] == "aceptada"
    assert db.boletas.docs[0]["estado"] == "usada"

    with pytest.raises(HTTPException) as error:
        ticket_service.validate(db, redis, _validator(), data)

    assert error.value.status_code == 409
    assert db.validaciones.docs[-1]["resultado"] == "ya_usada"


@pytest.mark.parametrize("estado", ["devuelta", "anulada"])
def test_boleta_devuelta_o_anulada_es_rechazada(estado):
    db = DB()
    redis = FakeRedis()
    ticket_id = f"bol_{estado}"
    code = ticket_id + "." + ticket_service._sign(ticket_id)
    db.boletas.docs.append({
        "_id": ticket_id,
        "codigo": code,
        "firma": ticket_service._sign(ticket_id),
        "estado": estado,
    })

    with pytest.raises(HTTPException) as error:
        ticket_service.validate(
            db,
            redis,
            _validator(),
            {"codigo": code, "puerta": "Principal"},
        )

    assert error.value.status_code == 409
    assert db.validaciones.docs[0]["resultado"] in (
        "boleta_devuelta",
        "boleta_anulada",
    )


def test_validaciones_simultaneas_solo_un_exito():
    db = DB()
    redis = FakeRedis()
    ticket_id = "bol_concurrent"
    code = ticket_id + "." + ticket_service._sign(ticket_id)
    db.boletas.docs.append({
        "_id": ticket_id,
        "codigo": code,
        "firma": ticket_service._sign(ticket_id),
        "estado": "valida",
    })
    data = {"codigo": code, "puerta": "Occidente"}

    def validate(index):
        try:
            ticket_service.validate(
                db,
                redis,
                dict(_validator(), _id=f"usr_{index}"),
                data,
            )
            return "aceptada"
        except HTTPException:
            return "rechazada"

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(validate, range(20)))

    assert results.count("aceptada") == 1
    assert results.count("rechazada") == 19
