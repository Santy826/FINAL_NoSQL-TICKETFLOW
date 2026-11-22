from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TicketValidate(BaseModel):
    codigo: str = Field(..., min_length=1)
    puerta: str = Field(..., min_length=1)


class TicketOut(BaseModel):
    id: str = Field(..., alias="_id")
    codigo: str
    firma: str
    qr: str
    ordenId: str
    compradorId: str
    funcionId: str
    seccion: str
    silla: str | None = None
    cantidad: int
    precio: float
    estado: Literal["valida", "usada", "devuelta", "anulada"]
    emitidaEn: str
    usadaEn: str | None = None

    model_config = {"populate_by_name": True}
