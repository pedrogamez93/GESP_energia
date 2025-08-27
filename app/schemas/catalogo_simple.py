# app/schemas/catalogo_simple.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class CatalogoSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config: from_attributes = True

class CatalogoDTO(CatalogoSelectDTO):
    Active: Optional[bool] = None  # algunos lo usan; si no, quedará en None

class CatalogoCreate(BaseModel):
    Nombre: Optional[str] = None

class CatalogoUpdate(BaseModel):
    Nombre: Optional[str] = None
    Active: Optional[bool] = None
