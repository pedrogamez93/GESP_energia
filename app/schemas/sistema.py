# app/schemas/sistema.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class SistemaSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config: from_attributes = True

class SistemaDTO(SistemaSelectDTO):
    Active: Optional[bool] = True

class SistemaCreate(BaseModel):
    Nombre: Optional[str] = None

class SistemaUpdate(BaseModel):
    Nombre: Optional[str] = None
    Active: Optional[bool] = None
