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
    db.boletas.create_index(
        [("funcionId", 1), ("silla", 1)],
        unique=True,
        partialFilterExpression={"estado": "valida"},
    )
    db.boletas.create_index("codigo", unique=True)
    db.validaciones.create_index([("boletaId", 1), ("fecha", -1)])


@asynccontextmanager
async def lifespan(app):
    connect_mongo()
    connect_redis()
    create_indexes()
    yield
    close_redis()
    close_mongo()
