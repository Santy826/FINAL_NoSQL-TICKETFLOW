from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class OrganizerCreate(BaseModel):
    razonSocial: str = Field(..., min_length=1, examples=["Productora Eventos S.A.S."])
    nit: str = Field(..., min_length=1, examples=["900123456-7"])
    contacto: EmailStr = Field(..., examples=["contacto@productora.com"])
    telefono: str | None = Field(None, examples=["+57 315 1234567"])
    comision: float = Field(..., ge=0, le=100, examples=[10.0])
    politicaDevolucion: str = Field("sin_devolucion", examples=["hasta_48h_antes"])


class OrganizerUpdate(BaseModel):
    razonSocial: str | None = None
    contacto: EmailStr | None = None
    telefono: str | None = None
    comision: float | None = Field(None, ge=0, le=100)
    politicaDevolucion: str | None = None


class OrganizerOut(BaseModel):
    id: str = Field(..., alias="_id")
    razonSocial: str
    nit: str
    contacto: str
    telefono: str | None = None
    comision: float
    politicaDevolucion: str

    model_config = {"populate_by_name": True}
