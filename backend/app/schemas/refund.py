from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RefundCreate(BaseModel):
    boletaId: str = Field(..., min_length=1)
    tipo: Literal["reembolso", "cambio_funcion"]
    motivo: str = Field(..., min_length=3)
    nuevaFuncionId: str | None = Field(None, min_length=1)


class RefundReject(BaseModel):
    motivo: str = Field(..., min_length=3)
