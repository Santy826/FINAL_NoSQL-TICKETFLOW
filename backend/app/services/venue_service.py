from fastapi import HTTPException, status
from app.repositories import venue_repo


def calcular_capacidad(secciones: list[dict]) -> int:
    total = 0
    for sec in secciones:
        tipo = sec.get("tipo")
        if tipo == "numerada":
            total += sum(f.get("sillas", 0) for f in sec.get("filas", []))
        elif tipo == "mesa":
            total += sum(m.get("capacidad", 0) for m in sec.get("mesas", []))
        elif tipo == "general":
            total += sec.get("capacidad", 0)
    return total


def validar_codigos_unicos(secciones: list[dict]):
    codigos = [s["codigo"] for s in secciones]
    if len(codigos) != len(set(codigos)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Los códigos de sección deben ser únicos dentro del recinto",
        )


def crear_recinto(db, data: dict):
    secciones = data.get("secciones", [])
    validar_codigos_unicos(secciones)
    data["capacidad_total"] = calcular_capacidad(secciones)
    return venue_repo.insert(db, data)


def listar_recintos(db, ciudad: str | None = None, tipo: str | None = None):
    filtros = {}
    if ciudad:
        filtros["ciudad"] = ciudad
    if tipo:
        filtros["tipo"] = tipo
    return venue_repo.find_all(db, filtros)


def obtener_recinto(db, venue_id: str):
    venue = venue_repo.find_by_id(db, venue_id)
    if not venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recinto no encontrado",
        )
    return venue


def actualizar_recinto(db, venue_id: str, data: dict):
    if "secciones" in data:
        validar_codigos_unicos(data["secciones"])
        data["capacidad_total"] = calcular_capacidad(data["secciones"])
    result = venue_repo.update(db, venue_id, data)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recinto no encontrado",
        )
    return result


def eliminar_recinto(db, venue_id: str):
    if not venue_repo.delete(db, venue_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recinto no encontrado",
        )
