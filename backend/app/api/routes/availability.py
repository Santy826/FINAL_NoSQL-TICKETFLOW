from fastapi import APIRouter

from app.api.dependencies import DbDep, RedisDep
from app.services import reservation_service

router = APIRouter(prefix="/api/v1/shows", tags=["Disponibilidad"])


@router.get("/{show_id}/availability")
def get_availability(show_id: str, db: DbDep, redis_cli: RedisDep):
    return reservation_service.availability(db, show_id, redis_cli)


@router.get("/{show_id}/seats")
def get_seats(show_id: str, db: DbDep, redis_cli: RedisDep):
    return reservation_service.seats(db, show_id, redis_cli)
