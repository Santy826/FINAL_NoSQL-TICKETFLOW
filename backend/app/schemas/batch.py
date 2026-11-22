from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BatchCreate(BaseModel):
    tipo: Literal["preventa", "ampliacion", "nueva_seccion", "nueva_funcion"]
    funcionId: str | None = Field(None, min_length=1)
    eventId: str | None = Field(None, min_length=1)
    seccion: str | None = Field(None, min_length=1)
    cantidad: int = Field(..., ge=1)
    precio: float = Field(..., gt=0)


class NewSectionBatch(BaseModel):
    tipo: Literal["nueva_seccion"]
    funcionId: str
    seccion: str
    cantidad: int = Field(..., ge=1)
    precio: float = Field(..., gt=0)
