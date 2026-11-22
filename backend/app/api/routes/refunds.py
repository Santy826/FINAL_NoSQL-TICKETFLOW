from fastapi import APIRouter, Depends, status

from app.api.dependencies import (
    CurrentUser,
    DbDep,
    RedisDep,
    require_role,
)
from app.schemas.refund import RefundCreate, RefundReject
from app.services import refund_service

router = APIRouter(prefix="/api/v1/refunds", tags=["Devoluciones"])
approval_roles = Depends(require_role("organizador", "administrador"))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_refund(
    body: RefundCreate,
    db: DbDep,
    redis_cli: RedisDep,
    user: CurrentUser,
):
    return refund_service.create(
        db,
        redis_cli,
        user,
        body.model_dump(exclude_none=True),
    )


@router.get("/{refund_id}")
def get_refund(refund_id: str, db: DbDep, user: CurrentUser):
    return refund_service.get(db, refund_id, user)


@router.patch("/{refund_id}/approve")
def approve_refund(
    refund_id: str,
    db: DbDep,
    redis_cli: RedisDep,
    user: CurrentUser,
    _authorized=approval_roles,
):
    return refund_service.approve(db, redis_cli, refund_id, user)


@router.patch("/{refund_id}/reject")
def reject_refund(
    refund_id: str,
    body: RefundReject,
    db: DbDep,
    user: CurrentUser,
    _authorized=approval_roles,
):
    return refund_service.reject(db, refund_id, user, body.motivo)
