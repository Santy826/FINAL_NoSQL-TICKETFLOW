from fastapi import APIRouter, Depends, status

from app.api.dependencies import (
    CurrentUser,
    DbDep,
    RedisDep,
    require_role,
)
from app.schemas.batch import BatchCreate
from app.services import batch_service

router = APIRouter(prefix="/api/v1/batches", tags=["Lotes"])
invoices_router = APIRouter(prefix="/api/v1/invoices", tags=["Facturas"])
require_batch_role = Depends(require_role("organizador", "administrador"))
require_invoice_role = Depends(require_role("organizador", "administrador"))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_batch(
    body: BatchCreate,
    db: DbDep,
    redis_cli: RedisDep,
    user: CurrentUser,
    _authorized=require_batch_role,
):
    return batch_service.create(
        db,
        redis_cli,
        user,
        body.model_dump(exclude_none=True),
    )


@invoices_router.get("")
def list_invoices(
    db: DbDep,
    user: CurrentUser,
    _authorized=require_invoice_role,
):
    return batch_service.list_invoices(db, user)
