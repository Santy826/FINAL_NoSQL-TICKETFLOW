from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    reservaId: str = Field(..., min_length=1)
    idempotencyKey: str = Field(..., min_length=1)
    metodoPago: Literal["simulado"] = "simulado"


class OrderItem(BaseModel):
    seccion: str
    silla: str | None = None
    cantidad: int = Field(..., ge=1)
    precioUnitario: float
    subtotal: float


class OrderOut(BaseModel):
    id: str = Field(..., alias="_id")
    idempotencyKey: str
    reservaId: str
    compradorId: str
    funcionId: str
    organizadorId: str
    categoria: str
    edadComprador: int | None = None
    items: list[dict]
    subtotal: float
    estado: Literal["pendiente", "pagada", "fallida", "reembolsada", "cancelada"]
    metodoPago: str
    fechaCreacion: str

    model_config = {"populate_by_name": True}
