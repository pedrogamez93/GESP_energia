from __future__ import annotations
from pydantic import BaseModel, Field

class CompatIn(BaseModel):
    TipoEquipoCalefaccionId: int = Field(..., ge=1)
    EnergeticoId: int = Field(..., ge=1)

class CompatOut(CompatIn):
    # Si tu tabla puente tiene PK compuesta sin 'Id', deja esto como opcional
    Id: int | None = None

    class Config:
        from_attributes = True
