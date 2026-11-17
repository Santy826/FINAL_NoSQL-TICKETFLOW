from __future__ import annotations

from datetime import date
from typing import Literal
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    nombre: str = Field(..., min_length=1, examples=["Juan Pérez"])
    correo: EmailStr = Field(..., examples=["juan@correo.com"])
    contrasena: str = Field(..., min_length=6, examples=["Segura123!"])
    fechaNacimiento: date = Field(..., examples=["2000-05-15"])
    rol: Literal["comprador", "organizador", "administrador", "validador"] = Field(
        "comprador"
    )


class UserOut(BaseModel):
    id: str = Field(..., alias="_id")
    nombre: str
    correo: str
    fechaNacimiento: str
    rol: str

    model_config = {"populate_by_name": True}


class LoginRequest(BaseModel):
    correo: EmailStr
    contrasena: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UserOut
