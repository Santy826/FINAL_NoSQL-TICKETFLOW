from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import CurrentUser, DbDep, RedisDep, require_role
from app.schemas.order import OrderCreate
from app.services import order_service

router = APIRouter(prefix="/api/v1/orders", tags=["Órdenes"])
users_router = APIRouter(prefix="/api/v1/users", tags=["Usuarios"])
require_buyer_or_admin = Depends(require_role("comprador", "administrador"))


@router.post("")
def pay_order(
    body: OrderCreate,
    db: DbDep,
    redis_cli: RedisDep,
    user: CurrentUser,
    _authorized=require_buyer_or_admin,
):
    order, created = order_service.pay(
        db,
        redis_cli,
        user,
        body.model_dump(mode="json"),
    )
    return JSONResponse(
        status_code=201 if created else 200,
        content=order,
    )


@router.get("/{order_id}")
def get_order(order_id: str, db: DbDep, user: CurrentUser):
    return order_service.get(db, order_id, user)


@users_router.get("/{buyer_id}/orders")
def get_user_orders(buyer_id: str, db: DbDep, user: CurrentUser):
    return order_service.get_for_user(db, buyer_id, user)
