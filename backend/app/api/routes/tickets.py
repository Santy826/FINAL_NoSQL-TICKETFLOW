from fastapi import APIRouter, Depends

from app.api.dependencies import (
    CurrentUser,
    DbDep,
    RedisDep,
    require_role,
)
from app.schemas.ticket import TicketValidate
from app.services import ticket_service

router = APIRouter(prefix="/api/v1/tickets", tags=["Boletas"])
require_validator_or_admin = Depends(require_role("validador", "administrador"))


@router.post("/validate")
def validate_ticket(
    body: TicketValidate,
    db: DbDep,
    redis_cli: RedisDep,
    user: CurrentUser,
    _authorized=require_validator_or_admin,
):
    return ticket_service.validate(
        db,
        redis_cli,
        user,
        body.model_dump(mode="json"),
    )


@router.get("/mine")
def get_my_tickets(db: DbDep, user: CurrentUser):
    return ticket_service.get_by_buyer(db, user["_id"], user)


@router.get("/{ticket_id}")
def get_ticket(ticket_id: str, db: DbDep, user: CurrentUser):
    return ticket_service.get(db, ticket_id, user)
