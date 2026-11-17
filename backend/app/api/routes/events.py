from fastapi import APIRouter, Depends, status

from app.api.dependencies import DbDep, require_role
from app.schemas.event import EventCreate, EventUpdate, FuncionCreate
from app.services import event_service

router = APIRouter(prefix="/api/v1/events", tags=["Eventos"])


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_evento(
    body: EventCreate,
    db: DbDep,
    _user=Depends(require_role("organizador", "administrador")),
):
    data = body.model_dump(mode="json")
    return event_service.crear_evento(db, data)


@router.get("")
def listar_eventos(
    db: DbDep,
    categoria: str | None = None,
    estado: str | None = None,
    ciudad: str | None = None,
):
    return event_service.listar_eventos(db, categoria=categoria, estado=estado, ciudad=ciudad)


@router.get("/{event_id}")
def obtener_evento(event_id: str, db: DbDep):
    return event_service.obtener_evento(db, event_id)


@router.patch("/{event_id}")
def actualizar_evento(
    event_id: str,
    body: EventUpdate,
    db: DbDep,
    _user=Depends(require_role("organizador", "administrador")),
):
    data = body.model_dump(exclude_none=True, mode="json")
    if not data:
        return event_service.obtener_evento(db, event_id)
    return event_service.actualizar_evento(db, event_id, data)


@router.patch("/{event_id}/cancel")
def cancelar_evento(
    event_id: str,
    db: DbDep,
    _user=Depends(require_role("organizador", "administrador")),
):
    return event_service.cancelar_evento(db, event_id)


@router.post("/{event_id}/shows", status_code=status.HTTP_201_CREATED)
def agregar_funciones(
    event_id: str,
    body: list[FuncionCreate],
    db: DbDep,
    _user=Depends(require_role("organizador", "administrador")),
):
    funciones = [f.model_dump(mode="json") for f in body]
    return event_service.agregar_funciones(db, event_id, funciones)
