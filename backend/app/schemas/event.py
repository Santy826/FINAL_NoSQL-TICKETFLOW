from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class FuncionCreate(BaseModel):
    fechaHora: datetime = Field(..., examples=["2027-01-23T20:00:00-05:00"])
    recintoId: str = Field(..., examples=["rec_03"])
    ciudad: str = Field(..., examples=["Cali"])
    estado: Literal["abierta", "cerrada", "cancelada"] = "abierta"
    precios: dict[str, float] = Field(
        ...,
        examples=[{"PLATEA": 180000, "BALCON": 120000, "GENERAL": 70000}],
    )


class EventCreate(BaseModel):
    nombre: str = Field(..., min_length=1, examples=["Noche de Comedia en Vivo"])
    categoria: Literal[
        "musica", "comedia", "teatro", "deportivo", "conferencia", "festival"
    ] = Field(..., examples=["comedia"])
    organizadorId: str = Field(..., examples=["org_010"])
    restriccionEdad: int | None = Field(None, ge=0, examples=[18])
    atributos: dict = Field(default_factory=dict, examples=[{"artistas": ["Artista A"]}])
    funciones: list[FuncionCreate] = Field(default_factory=list)


class EventUpdate(BaseModel):
    nombre: str | None = None
    categoria: Literal[
        "musica", "comedia", "teatro", "deportivo", "conferencia", "festival"
    ] | None = None
    restriccionEdad: int | None = None
    atributos: dict | None = None


class FuncionOut(BaseModel):
    funcionId: str
    fechaHora: str
    recintoId: str
    ciudad: str
    estado: str
    precios: dict[str, float]


class EventOut(BaseModel):
    id: str = Field(..., alias="_id")
    nombre: str
    categoria: str
    organizadorId: str
    estado: str
    restriccionEdad: int | None = None
    atributos: dict
    funciones: list[dict]

    model_config = {"populate_by_name": True}
