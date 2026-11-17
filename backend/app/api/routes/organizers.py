from fastapi import APIRouter, Depends, status

from app.api.dependencies import DbDep, require_role, get_current_user
from app.schemas.organizer import OrganizerCreate, OrganizerUpdate
from app.services import organizer_service

router = APIRouter(prefix="/api/v1/organizers", tags=["Organizadores"])


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_organizador(
    body: OrganizerCreate,
    db: DbDep,
    _user=Depends(require_role("administrador")),
):
    data = body.model_dump(mode="json")
    return organizer_service.crear_organizador(db, data)


@router.get("")
def listar_organizadores(
    db: DbDep,
    _user=Depends(get_current_user),
):
    return organizer_service.listar_organizadores(db)


@router.get("/{org_id}")
def obtener_organizador(
    org_id: str,
    db: DbDep,
    _user=Depends(get_current_user),
):
    return organizer_service.obtener_organizador(db, org_id)


@router.patch("/{org_id}")
def actualizar_organizador(
    org_id: str,
    body: OrganizerUpdate,
    db: DbDep,
    _user=Depends(require_role("administrador")),
):
    data = body.model_dump(exclude_none=True, mode="json")
    if not data:
        return organizer_service.obtener_organizador(db, org_id)
    return organizer_service.actualizar_organizador(db, org_id, data)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_organizador(
    org_id: str,
    db: DbDep,
    _user=Depends(require_role("administrador")),
):
    organizer_service.eliminar_organizador(db, org_id)


@router.get("/{org_id}/events")
def listar_eventos_organizador(
    org_id: str,
    db: DbDep,
    _user=Depends(get_current_user),
):
    organizer_service.obtener_organizador(db, org_id)
    from app.repositories import event_repo
    return event_repo.find_by_organizer(db, org_id)
