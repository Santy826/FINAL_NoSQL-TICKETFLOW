from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.venues import router as venues_router
from app.api.routes.organizers import router as organizers_router
from app.api.routes.events import router as events_router
from app.api.routes.availability import router as availability_router
from app.api.routes.reservations import router as reservations_router
from app.api.routes.orders import router as orders_router
from app.api.routes.orders import users_router
from app.api.routes.tickets import router as tickets_router
from app.api.routes.batches import invoices_router
from app.api.routes.batches import router as batches_router
from app.api.routes.refunds import router as refunds_router
from app.api.routes.reports import router as reports_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(venues_router)
api_router.include_router(organizers_router)
api_router.include_router(events_router)
api_router.include_router(availability_router)
api_router.include_router(reservations_router)
api_router.include_router(orders_router)
api_router.include_router(users_router)
api_router.include_router(tickets_router)
api_router.include_router(batches_router)
api_router.include_router(invoices_router)
api_router.include_router(refunds_router)
api_router.include_router(reports_router)
