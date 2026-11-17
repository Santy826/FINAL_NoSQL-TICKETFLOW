from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.database import get_db, get_redis
from app.core.security import decode_access_token

security = HTTPBearer(auto_error=False)


def _get_db():
    database = get_db()
    if database is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    return database


def _get_redis():
    r = get_redis()
    if r is None:
        raise HTTPException(status_code=503, detail="Redis no disponible")
    return r


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    db=Depends(_get_db),
    redis_cli=Depends(_get_redis),
):
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no proporcionado",
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )

    session_key = f"sesion:{token}"
    if not redis_cli.exists(session_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada o cerrada",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin sujeto",
        )

    from app.repositories.user_repo import find_by_id

    user = find_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )

    return user


def require_role(*roles: str):
    def _check(current_user=Depends(get_current_user)):
        if current_user.get("rol") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol: {', '.join(roles)}",
            )
        return current_user

    return _check


DbDep = Annotated[object, Depends(_get_db)]
RedisDep = Annotated[object, Depends(_get_redis)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
