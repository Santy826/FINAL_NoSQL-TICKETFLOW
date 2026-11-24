from fastapi import HTTPException, status
from app.repositories import event_repo, organizer_repo, venue_repo


def _validar_organizador(db, organizer_id: str):
    if not organizer_repo.find_by_id(db, organizer_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organizador '{organizer_id}' no encontrado",
        )


def _validar_recintos_funciones(db, funciones: list[dict]):
    for func in funciones:
        recinto = venue_repo.find_by_id(db, func["recintoId"])
        if not recinto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recinto '{func['recintoId']}' no encontrado",
            )
        ciudad_recinto = recinto.get("ciudad")
        if ciudad_recinto and func.get("ciudad") and func["ciudad"] != ciudad_recinto:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"La función debe realizarse en la ciudad del recinto "
                    f"('{ciudad_recinto}')"
                ),
            )
        codigos_recinto = {s["codigo"] for s in recinto.get("secciones", [])}
        codigos_precios = set(func.get("precios", {}).keys())
        invalidos = codigos_precios - codigos_recinto
        if invalidos:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Secciones no válidas para el recinto: {invalidos}",
            )


def crear_evento(db, data: dict) -> dict:
    _validar_organizador(db, data["organizadorId"])
    if data.get("funciones"):
        _validar_recintos_funciones(db, data["funciones"])
    return event_repo.insert(db, data)


def listar_eventos(
    db,
    categoria: str | None = None,
    estado: str | None = None,
    ciudad: str | None = None,
):
    filtros = {}
    if categoria:
        filtros["categoria"] = categoria
    if estado:
        filtros["estado"] = estado
    if ciudad:
        filtros["funciones.ciudad"] = ciudad
    events = event_repo.find_all(db, filtros)
    return events


def obtener_evento(db, event_id: str):
    evento = event_repo.find_by_id(db, event_id)
    if not evento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )
    return evento


def actualizar_evento(db, event_id: str, data: dict):
    result = event_repo.update(db, event_id, data)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )
    return result


def cancelar_evento(db, event_id: str):
    result = event_repo.cancel(db, event_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado o ya cancelado",
        )
    return result


def publicar_evento(db, event_id: str):
    result = event_repo.update(db, event_id, {"estado": "publicado"})
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )
    return result


def agregar_funciones(db, event_id: str, funciones: list[dict]):
    obtener_evento(db, event_id)
    _validar_recintos_funciones(db, funciones)
    for func in funciones:
        if hasattr(func.get("fechaHora"), "isoformat"):
            func["fechaHora"] = func["fechaHora"].isoformat()
    result = event_repo.add_shows(db, event_id, funciones)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )
    return result
