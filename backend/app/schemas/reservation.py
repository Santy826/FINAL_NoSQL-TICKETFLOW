from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReservationItem(BaseModel):
    seccion: str = Field(..., min_length=1)
    silla: str | None = Field(None, min_length=1)
    cantidad: int = Field(1, ge=1)


class ReservationCreate(BaseModel):
    funcionId: str = Field(..., min_length=1)
    items: list[ReservationItem] = Field(..., min_length=1)


class ReservationOut(BaseModel):
    id: str = Field(..., alias="_id")
    funcionId: str
    usuarioId: str
    items: list[dict]
    estado: Literal["activa", "cancelada", "expirada"]
    creadaEn: str
    expiraEn: str

    model_config = {"populate_by_name": True}
