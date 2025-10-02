# app/schemas/unidad_medida.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List

class UnidadMedidaDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    Abrv: Optional[str] = None          # <-- nuevo

    class Config:
        from_attributes = True

class UnidadMedidaCreate(BaseModel):
    Nombre: str
    Abrv: Optional[str] = None          # <-- nuevo

class UnidadMedidaUpdate(BaseModel):
    Nombre: str
    Abrv: Optional[str] = None          # <-- nuevo

class UnidadMedidaPage(BaseModel):
    total: int = 0
    data: List[UnidadMedidaDTO] = Field(default_factory=list)

    class Config:
        from_attributes = True
