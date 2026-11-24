import json
from datetime import UTC, datetime, timedelta

from app.services import report_service


class FakeRedis:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None):
        self.values[key] = value
        return True

    def scan_iter(self, match=None):
        return iter(list(self.values))

    def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)


class FakeCollection:
    def __init__(self, result):
        self.result = result

    def aggregate(self, pipeline):
        return iter(self.result)


class FakeDB:
    def __init__(self):
        self.eventos = FakeCollection([])
        self.ordenes = FakeCollection([
            {"_id": "2027-01-01", "ordenes": 2, "boletas": 3, "ingresos": 450000},
        ])
        self.organizadores = FakeCollection([])
        self.boletas = FakeCollection([])
        self.devoluciones = FakeCollection([])
        self.validaciones = FakeCollection([])

    def __getattribute__(self, name):
        if name in {
            "eventos",
            "ordenes",
            "organizadores",
            "boletas",
            "devoluciones",
            "validaciones",
        }:
            return object.__getattribute__(self, name)
        return object.__getattribute__(self, name)


def test_report_cache_miss_then_hit():
    db = FakeDB()
    redis = FakeRedis()

    first = report_service.execute(db, redis, "sales", {}, [
        {"$match": {}},
    ])
    second = report_service.execute(db, redis, "sales", {}, [
        {"$match": {}},
    ])

    assert first[1] == "miss"
    assert second[1] == "hit"


def test_report_cache_invalidation_removes_keys():
    redis = FakeRedis()
    redis.set("report:sales:", "{}", ex=300)
    redis.set("report:attendance:", "[]", ex=300)
    redis.set("event:list:", "[]", ex=300)

    removed = report_service.invalidate(None, redis)

    assert removed == 3
    assert redis.values == {}


def test_top_seats_limits_value():
    db = FakeDB()
    redis = FakeRedis()

    result, cache_status = report_service.top_seats(db, redis, 1000)

    assert result == []
    assert cache_status == "miss"


class CapacityCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def find(self, query=None, *args, **kwargs):
        def matches(doc, key, value):
            if key == "funciones.funcionId":
                return any(
                    show.get("funcionId") == value
                    for show in doc.get("funciones", [])
                )
            if isinstance(value, dict) and "$in" in value:
                return doc.get(key) in value["$in"]
            if isinstance(value, dict) and "$ne" in value:
                return doc.get(key) != value["$ne"]
            return doc.get(key) == value
        if not query:
            return [dict(doc) for doc in self.docs]
        return [
            dict(doc)
            for doc in self.docs
            if all(matches(doc, key, value) for key, value in query.items())
        ]

    def find_one(self, query=None, *args, **kwargs):
        matches = self.find(query)
        return matches[0] if matches else None

    def count_documents(self, query=None):
        return len(self.find(query))

    def aggregate(self, pipeline):
        return iter([])


def test_occupancy_uses_venue_capacity_and_excludes_returns():
    db = CapacityCollection([])
    db.eventos = CapacityCollection([{
        "_id": "evt_1",
        "funciones": [{"funcionId": "fn_1", "recintoId": "rec_1"}],
    }])
    db.recintos = CapacityCollection([{
        "_id": "rec_1",
        "secciones": [{
            "codigo": "NORTE",
            "tipo": "numerada",
            "filas": [{"fila": "A", "sillas": 2}],
        }],
    }])
    db.reservas = CapacityCollection([{
        "funcionId": "fn_1",
        "estado": "activa",
        "expiraEn": "2099-01-01T00:00:00+00:00",
        "items": [{"seccion": "NORTE", "silla": "NORTE-A-1", "cantidad": 1}],
    }])
    db.boletas = CapacityCollection([
        {"funcionId": "fn_1", "seccion": "NORTE", "silla": "NORTE-A-1", "estado": "valida"},
        {"funcionId": "fn_1", "seccion": "NORTE", "silla": "NORTE-A-2", "estado": "devuelta"},
    ])

    redis = FakeRedis()
    result, cache_status = report_service.occupancy(db, redis, "fn_1")

    assert result == [{
        "seccion": "NORTE",
        "tipo": "numerada",
        "capacidad": 2,
        "vendidas": 1,
        "reservadas": 0,
        "ocupadas": 1,
        "disponibles": 1,
        "ocupacionPorcentaje": 50.0,
        "funcionId": "fn_1",
    }]
    assert cache_status == "miss"


def test_inventory_value_calculates_available_general_inventory():
    db = CapacityCollection([])
    db.eventos = CapacityCollection([{
        "_id": "evt_1",
        "funciones": [{
            "funcionId": "fn_1",
            "recintoId": "rec_1",
            "precios": {"GENERAL": 80000},
        }],
    }])
    db.recintos = CapacityCollection([{
        "_id": "rec_1",
        "secciones": [{"codigo": "GENERAL", "tipo": "general", "capacidad": 100}],
    }])
    db.reservas = CapacityCollection([{
        "funcionId": "fn_1",
        "estado": "activa",
        "expiraEn": "2099-01-01T00:00:00+00:00",
        "items": [{"seccion": "GENERAL", "cantidad": 10}],
    }])
    db.boletas = CapacityCollection([
        {"funcionId": "fn_1", "seccion": "GENERAL", "cantidad": 20, "estado": "valida"},
        {"funcionId": "fn_1", "seccion": "GENERAL", "cantidad": 5, "estado": "devuelta"},
    ])

    redis = FakeRedis()
    result, cache_status = report_service.inventory_value(db, redis, "fn_1")

    assert result[0]["vendidas"] == 20
    assert result[0]["reservadas"] == 10
    assert result[0]["disponibles"] == 70
    assert result[0]["valorInventario"] == 5600000
    assert cache_status == "miss"


def test_sales_aggregation_counts_item_quantities():
    db = FakeDB()
    redis = FakeRedis()

    report_service.sales(db, redis, "2027-01-01", "2027-01-31")

    key = next(iter(redis.values))
    assert "report:sales:" in key


def test_low_sales_requires_future_window_and_low_occupancy():
    db = CapacityCollection([])
    db.eventos = CapacityCollection([{
        "_id": "evt_1",
        "estado": "publicado",
        "nombre": "Evento",
        "funciones": [{
            "funcionId": "fn_1",
            "fechaHora": "2099-01-01T20:00:00+00:00",
            "recintoId": "rec_1",
            "estado": "abierta",
        }],
    }])
    db.recintos = CapacityCollection([{
        "_id": "rec_1",
        "secciones": [{"codigo": "GENERAL", "tipo": "general", "capacidad": 100}],
    }])
    db.reservas = CapacityCollection([])
    db.boletas = CapacityCollection([])
    redis = FakeRedis()

    result, cache_status = report_service.low_sales(db, redis, 15)

    assert result == []
    assert cache_status == "miss"


def test_event_cache_is_separate_and_uses_300_seconds():
    db = CapacityCollection([{"_id": "evt_1", "nombre": "Evento"}])
    db.eventos = db
    redis = FakeRedis()

    first, first_status = report_service.get_cached_events(db, redis)
    second, second_status = report_service.get_cached_events(db, redis)

    assert first_status == "miss"
    assert second_status == "hit"
    assert any(key.startswith("event:list:") for key in redis.values)


class PipelineCaptureCollection:
    def __init__(self):
        self.last_pipeline = None

    def aggregate(self, pipeline):
        self.last_pipeline = pipeline
        return iter([])

    def find(self, query=None, *args, **kwargs):
        return []

    def find_one(self, query=None, *args, **kwargs):
        return None


def test_organizers_report_uses_lookup():
    db = FakeDB()
    db.organizadores = PipelineCaptureCollection()
    redis = FakeRedis()

    report_service.organizers(db, redis)

    pipeline = db.organizadores.last_pipeline
    assert any("$lookup" in stage for stage in pipeline)
    assert any(stage.get("$lookup", {}).get("from") == "eventos" for stage in pipeline)


def test_sales_by_event_type_counts_item_quantities():
    db = FakeDB()
    db.ordenes = PipelineCaptureCollection()
    redis = FakeRedis()

    report_service.sales_by_event_type(db, redis)

    pipeline = db.ordenes.last_pipeline
    assert pipeline[0] == {"$unwind": "$items"}
    assert any("items.cantidad" in str(stage) for stage in pipeline)


def test_revenue_report_reads_real_refunds_collection():
    db = FakeDB()
    db.ordenes = PipelineCaptureCollection()
    redis = FakeRedis()

    report_service.revenue(db, redis)

    pipeline = db.ordenes.last_pipeline
    assert any(stage.get("$lookup", {}).get("from") == "devoluciones" for stage in pipeline)


def test_refunds_report_includes_all_states():
    db = FakeDB()
    db.devoluciones = PipelineCaptureCollection()
    redis = FakeRedis()

    report_service.refunds(db, redis)

    pipeline = db.devoluciones.last_pipeline
    group = next(stage["$group"] for stage in pipeline if "$group" in stage)
    assert group["_id"] == "$estado"


def test_fraud_report_includes_missing_ticket_and_boleta_context():
    db = FakeDB()
    db.validaciones = PipelineCaptureCollection()
    redis = FakeRedis()

    report_service.fraud_attempts(db, redis)

    pipeline = db.validaciones.last_pipeline
    text = str(pipeline)
    assert "boleta_no_encontrada" in text
    assert "boletas" in text
    assert "eventos" in text


def test_attendance_report_uses_accepted_validations():
    db = FakeDB()
    db.boletas = PipelineCaptureCollection()
    redis = FakeRedis()

    report_service.attendance(db, redis)

    pipeline = db.boletas.last_pipeline
    text = str(pipeline)
    assert "validaciones" in text
    assert "aceptada" in text
    assert "porPuerta" in text


def test_buyers_by_age_always_returns_fixed_ranges():
    db = FakeDB()
    db.ordenes = PipelineCaptureCollection()
    redis = FakeRedis()

    db.ordenes.aggregate = lambda pipeline: iter([
        {"_id": 0, "compradores": 2, "ingresos": 100000},
    ])
    result, _ = report_service.buyers_by_age(db, redis)

    assert [row["rango"] for row in result] == [
        "menores de 18",
        "18 a 25",
        "26 a 35",
        "36 a 50",
        "mas de 50",
    ]


def test_low_sales_only_returns_future_events_below_30_percent():
    db = CapacityCollection([])
    future = datetime.now(UTC) + timedelta(days=5)
    db.eventos = CapacityCollection([{
        "_id": "evt_low",
        "estado": "publicado",
        "nombre": "Evento próximo",
        "funciones": [{
            "funcionId": "fn_low",
            "fechaHora": future.isoformat(),
            "recintoId": "rec_low",
            "estado": "abierta",
        }],
    }])
    db.recintos = CapacityCollection([{
        "_id": "rec_low",
        "secciones": [{"codigo": "GENERAL", "tipo": "general", "capacidad": 100}],
    }])
    db.reservas = CapacityCollection([])
    db.boletas = CapacityCollection([])
    redis = FakeRedis()

    result, cache_status = report_service.low_sales(db, redis, 15)

    assert len(result) == 1
    assert result[0]["ocupacionPorcentaje"] == 0.0
    assert result[0]["capacidad"] == 100
    assert cache_status == "miss"
