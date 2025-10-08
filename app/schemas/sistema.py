from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SistemaSelectDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: int
    Nombre: Optional[str] = None


class SistemaDTO(SistemaSelectDTO):
    Active: Optional[bool] = True


class SistemaCreate(BaseModel):
    Nombre: Optional[str] = None


class SistemaUpdate(BaseModel):
    Nombre: Optional[str] = None
    Active: Optional[bool] = None
