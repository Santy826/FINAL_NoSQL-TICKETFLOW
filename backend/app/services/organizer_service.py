from fastapi import HTTPException, status
from app.repositories import organizer_repo


def crear_organizador(db, data: dict) -> dict:
    if organizer_repo.find_by_nit(db, data["nit"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un organizador con ese NIT",
        )
    return organizer_repo.insert(db, data)


def listar_organizadores(db):
    return organizer_repo.find_all(db)


def obtener_organizador(db, org_id: str):
    org = organizer_repo.find_by_id(db, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organizador no encontrado",
        )
    return org


def actualizar_organizador(db, org_id: str, data: dict):
    result = organizer_repo.update(db, org_id, data)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organizador no encontrado",
        )
    return result


def eliminar_organizador(db, org_id: str):
    if not organizer_repo.delete(db, org_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organizador no encontrado",
        )
