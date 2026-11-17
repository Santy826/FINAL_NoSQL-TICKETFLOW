from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class FilaSchema(BaseModel):
    fila: str = Field(..., examples=["A"])
    sillas: int = Field(..., gt=0, examples=[20])


class MesaSchema(BaseModel):
    mesa: str = Field(..., examples=["M1"])
    capacidad: int = Field(..., gt=0, examples=[6])


class SeccionNumerada(BaseModel):
    codigo: str = Field(..., examples=["PLATEA"])
    tipo: Literal["numerada"] = "numerada"
    filas: list[FilaSchema] = Field(..., min_length=1)


class SeccionMesa(BaseModel):
    codigo: str = Field(..., examples=["PRINCIPAL"])
    tipo: Literal["mesa"] = "mesa"
    mesas: list[MesaSchema] = Field(..., min_length=1)


class SeccionGeneral(BaseModel):
    codigo: str = Field(..., examples=["GENERAL"])
    tipo: Literal["general"] = "general"
    capacidad: int = Field(..., gt=0, examples=[300])


SeccionSchema = SeccionNumerada | SeccionMesa | SeccionGeneral


class VenueCreate(BaseModel):
    nombre: str = Field(..., min_length=1, examples=["Teatro Municipal"])
    tipo: str = Field(..., examples=["teatro"])
    ciudad: str = Field(..., examples=["Cali"])
    direccion: str | None = Field(None, examples=["Cra 5 # 6-32"])
    secciones: list[SeccionSchema] = Field(..., min_length=1)


class VenueUpdate(BaseModel):
    nombre: str | None = None
    tipo: str | None = None
    ciudad: str | None = None
    direccion: str | None = None
    secciones: list[SeccionSchema] | None = None


class VenueOut(BaseModel):
    id: str = Field(..., alias="_id")
    nombre: str
    tipo: str
    ciudad: str
    direccion: str | None = None
    secciones: list[dict]
    capacidad_total: int = 0

    model_config = {"populate_by_name": True}
