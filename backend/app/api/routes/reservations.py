from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentUser, DbDep, RedisDep
from app.schemas.reservation import ReservationCreate
from app.services import reservation_service

router = APIRouter(prefix="/api/v1/reservations", tags=["Reservas"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_reservation(
    body: ReservationCreate,
    db: DbDep,
    redis_cli: RedisDep,
    user: CurrentUser,
):
    return reservation_service.create(
        db,
        redis_cli,
        user["_id"],
        body.funcionId,
        [item.model_dump() for item in body.items],
    )


@router.get("/{reservation_id}")
def get_reservation(reservation_id: str, db: DbDep, redis_cli: RedisDep, user: CurrentUser):
    return reservation_service.get(db, redis_cli, reservation_id, user["_id"])


@router.delete("/{reservation_id}")
def cancel_reservation(
    reservation_id: str,
    db: DbDep,
    redis_cli: RedisDep,
    user: CurrentUser,
):
    return reservation_service.cancel(db, redis_cli, reservation_id, user["_id"])
