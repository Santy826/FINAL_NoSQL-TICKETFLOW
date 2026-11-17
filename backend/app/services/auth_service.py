from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories import user_repo


def registrar_usuario(db, data: dict) -> dict:
    if user_repo.find_by_email(db, data["correo"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese correo",
        )

    data["contrasenaHash"] = hash_password(data.pop("contrasena"))
    if hasattr(data.get("fechaNacimiento"), "isoformat"):
        data["fechaNacimiento"] = data["fechaNacimiento"].isoformat()

    doc = user_repo.insert(db, data)
    doc.pop("contrasenaHash", None)
    return doc


def login(db, redis_cli, correo: str, contrasena: str) -> dict:
    user = user_repo.find_by_email(db, correo)
    if not user or not verify_password(contrasena, user.get("contrasenaHash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )

    token = create_access_token(data={"sub": user["_id"], "rol": user["rol"]})

    session_key = f"sesion:{token}"
    redis_cli.hset(session_key, mapping={
        "userId": user["_id"],
        "nombre": user["nombre"],
        "rol": user["rol"],
    })
    redis_cli.expire(session_key, settings.SESSION_TTL_SECONDS)

    user_out = {k: v for k, v in user.items() if k != "contrasenaHash"}
    return {"access_token": token, "token_type": "bearer", "usuario": user_out}


def logout(redis_cli, token: str) -> None:
    session_key = f"sesion:{token}"
    redis_cli.delete(session_key)
