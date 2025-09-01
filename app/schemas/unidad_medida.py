from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List

class UnidadMedidaDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None

    class Config:
        from_attributes = True


class UnidadMedidaCreate(BaseModel):
    Nombre: str


class UnidadMedidaUpdate(BaseModel):
    Nombre: str


# Wrapper de paginación para listado
class UnidadMedidaPage(BaseModel):
    total: int = 0
    data: List[UnidadMedidaDTO] = Field(default_factory=list)

    class Config:
        from_attributes = True
