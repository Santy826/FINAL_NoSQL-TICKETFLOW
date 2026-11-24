from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import DbDep, RedisDep, require_role
from app.services import report_service

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["Reportes"],
)
report_roles = Depends(require_role("administrador", "organizador"))


def _respond(response: Response, result: tuple[list | dict, str]):
    data, cache_status = result
    response.headers["X-Cache"] = cache_status
    return data


@router.get("/occupancy", summary="R-01 Ocupación por función y sección")
def occupancy(response: Response, db: DbDep, redis_cli: RedisDep, funcion_id: str | None = Query(None), seccion: str | None = Query(None), _user=report_roles):
    return _respond(response, report_service.occupancy(db, redis_cli, funcion_id, seccion))


@router.get("/inventory-value", summary="R-02 Valor del inventario")
def inventory_value(response: Response, db: DbDep, redis_cli: RedisDep, funcion_id: str | None = Query(None), _user=report_roles):
    return _respond(response, report_service.inventory_value(db, redis_cli, funcion_id))


@router.get("/sales", summary="R-03 Boletas vendidas por rango de fechas")
def sales(response: Response, db: DbDep, redis_cli: RedisDep, desde: str | None = Query(None), hasta: str | None = Query(None), evento_id: str | None = Query(None), _user=report_roles):
    return _respond(response, report_service.sales(db, redis_cli, desde, hasta, evento_id))


@router.get("/organizers", summary="R-04 Organizadores y eventos")
def organizers(response: Response, db: DbDep, redis_cli: RedisDep, _user=report_roles):
    return _respond(response, report_service.organizers(db, redis_cli))


@router.get("/show-availability", summary="R-05 Disponibilidad por evento y función")
def show_availability(response: Response, db: DbDep, redis_cli: RedisDep, evento_id: str | None = Query(None), _user=report_roles):
    return _respond(response, report_service.show_availability(db, redis_cli, evento_id))


@router.get("/buyers-by-age", summary="R-06 Compradores por rango de edad")
def buyers_by_age(response: Response, db: DbDep, redis_cli: RedisDep, desde: str | None = Query(None), hasta: str | None = Query(None), evento_id: str | None = Query(None), _user=report_roles):
    return _respond(response, report_service.buyers_by_age(db, redis_cli, desde, hasta, evento_id))


@router.get("/top-seats", summary="R-08 Sillas más vendidas")
def top_seats(response: Response, db: DbDep, redis_cli: RedisDep, limite: int = Query(10, ge=1, le=100), _user=report_roles):
    return _respond(response, report_service.top_seats(db, redis_cli, limite))


@router.get("/sales-by-type", summary="R-07 Ventas por tipo de evento")
def sales_by_event_type(response: Response, db: DbDep, redis_cli: RedisDep, _user=report_roles):
    return _respond(response, report_service.sales_by_event_type(db, redis_cli))


@router.get("/revenue", summary="R-09 Ingresos por organizador")
def revenue(response: Response, db: DbDep, redis_cli: RedisDep, _user=report_roles):
    return _respond(response, report_service.revenue(db, redis_cli))


@router.get("/low-sales", summary="R-10 Eventos próximos con baja venta")
def low_sales(response: Response, db: DbDep, redis_cli: RedisDep, dias: int = Query(15, ge=1, le=365), _user=report_roles):
    return _respond(response, report_service.low_sales(db, redis_cli, dias))


@router.get("/refunds", summary="R-11 Devoluciones")
def refunds(response: Response, db: DbDep, redis_cli: RedisDep, desde: str | None = Query(None), hasta: str | None = Query(None), _user=report_roles):
    return _respond(response, report_service.refunds(db, redis_cli, desde, hasta))


@router.get("/fraud-attempts", summary="R-12 Intentos de fraude")
def fraud_attempts(response: Response, db: DbDep, redis_cli: RedisDep, _user=report_roles):
    return _respond(response, report_service.fraud_attempts(db, redis_cli))


@router.get("/attendance", summary="R-13 Asistencia")
def attendance(response: Response, db: DbDep, redis_cli: RedisDep, funcion_id: str | None = Query(None), _user=report_roles):
    return _respond(response, report_service.attendance(db, redis_cli, funcion_id))
