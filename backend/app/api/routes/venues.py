from fastapi import APIRouter, Depends, status

from app.api.dependencies import DbDep, require_role, get_current_user
from app.schemas.venue import VenueCreate, VenueOut, VenueUpdate
from app.services import venue_service

router = APIRouter(prefix="/api/v1/venues", tags=["Recintos"])


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_recinto(
    body: VenueCreate,
    db: DbDep,
    _user=Depends(require_role("administrador")),
):
    data = body.model_dump(mode="json")
    return venue_service.crear_recinto(db, data)


@router.get("")
def listar_recintos(
    db: DbDep,
    _user=Depends(get_current_user),
    ciudad: str | None = None,
    tipo: str | None = None,
):
    return venue_service.listar_recintos(db, ciudad=ciudad, tipo=tipo)


@router.get("/{venue_id}")
def obtener_recinto(
    venue_id: str,
    db: DbDep,
    _user=Depends(get_current_user),
):
    return venue_service.obtener_recinto(db, venue_id)


@router.patch("/{venue_id}")
def actualizar_recinto(
    venue_id: str,
    body: VenueUpdate,
    db: DbDep,
    _user=Depends(require_role("administrador")),
):
    data = body.model_dump(exclude_none=True, mode="json")
    if not data:
        return venue_service.obtener_recinto(db, venue_id)
    return venue_service.actualizar_recinto(db, venue_id, data)


@router.delete("/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_recinto(
    venue_id: str,
    db: DbDep,
    _user=Depends(require_role("administrador")),
):
    venue_service.eliminar_recinto(db, venue_id)
