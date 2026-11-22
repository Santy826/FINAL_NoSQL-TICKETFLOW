import asyncio
from contextlib import asynccontextmanager

import redis
from pymongo import MongoClient

from app.core.config import settings

mongo_client: MongoClient | None = None
db = None
redis_client: redis.Redis | None = None


def connect_mongo():
    global mongo_client, db
    mongo_client = MongoClient(settings.MONGO_URI)
    db = mongo_client[settings.MONGO_DATABASE]


def close_mongo():
    global mongo_client, db
    if mongo_client:
        mongo_client.close()
        mongo_client = None
        db = None


def connect_redis():
    global redis_client
    redis_client = redis.from_url(settings.REDIS_URI, decode_responses=True)


def close_redis():
    global redis_client
    if redis_client:
        redis_client.close()
        redis_client = None


def get_db():
    return db


def get_redis():
    return redis_client


def create_indexes():
    if db is None:
        return

    db.usuarios.create_index("correo", unique=True)
    db.eventos.create_index([
        ("estado", 1),
        ("categoria", 1),
        ("funciones.fechaHora", 1),
    ])
    db.ordenes.create_index(
        "idempotencyKey",
        unique=True,
        partialFilterExpression={"idempotencyKey": {"$exists": True}},
    )
    db.ordenes.create_index([("compradorId", 1), ("fechaCreacion", -1)])
    db.ordenes.create_index([("funcionId", 1), ("estado", 1)])
    try:
        db.boletas.drop_index("funcionId_1_silla_1")
    except Exception:
        pass
    db.boletas.create_index(
        [("funcionId", 1), ("silla", 1)],
        unique=True,
        partialFilterExpression={
            "estado": {"$in": ["valida", "usada"]},
            "silla": {"$type": "string"},
        },
    )
    db.boletas.create_index("codigo", unique=True)
    db.validaciones.create_index([("boletaId", 1), ("fecha", -1)])
    db.reservas.create_index([("funcionId", 1), ("estado", 1), ("expiraEn", 1)])
    db.reservas.create_index([("usuarioId", 1), ("creadaEn", -1)])
    db.lotes.create_index([("funcionId", 1), ("estado", 1), ("creadoEn", -1)])
    db.lotes.create_index([("organizadorId", 1), ("creadoEn", -1)])
    db.facturas.create_index("loteId", unique=True)
    db.facturas.create_index([("organizadorId", 1), ("fechaEmision", -1)])
    db.devoluciones.create_index([("compradorId", 1), ("solicitadaEn", -1)])
    db.devoluciones.create_index([("boletaId", 1), ("estado", 1)])


async def _reservation_expiration_worker():
    from app.services.reservation_service import expire_active_reservations

    while True:
        await asyncio.sleep(5)
        if db is not None and redis_client is not None:
            await asyncio.to_thread(expire_active_reservations, db, redis_client)


@asynccontextmanager
async def lifespan(app):
    connect_mongo()
    connect_redis()
    create_indexes()
    worker = asyncio.create_task(_reservation_expiration_worker())
    yield
    worker.cancel()
    await asyncio.gather(worker, return_exceptions=True)
    close_redis()
    close_mongo()
