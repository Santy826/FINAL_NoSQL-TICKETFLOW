from typing import Annotated
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import DbDep, RedisDep, get_current_user, security
from app.schemas.user import UserCreate, LoginRequest
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: DbDep):
    data = body.model_dump(mode="json")
    return auth_service.registrar_usuario(db, data)


@router.post("/login")
def login(body: LoginRequest, db: DbDep, redis_cli: RedisDep):
    return auth_service.login(db, redis_cli, body.correo, body.contrasena)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    redis_cli: RedisDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    _user=Depends(get_current_user),
):
    if credentials and credentials.credentials:
        auth_service.logout(redis_cli, credentials.credentials)
