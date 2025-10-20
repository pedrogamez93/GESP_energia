# app/schemas/catalogo_simple.py
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class CatalogoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: int
    Nombre: Optional[str] = None
    Active: Optional[bool] = True

class CatalogoCreate(BaseModel):
    Nombre: Optional[str] = None

class CatalogoUpdate(BaseModel):
    Nombre: Optional[str] = None
    Active: Optional[bool] = None

# 👇 NUEVO: envoltorio de paginación tipado
class CatalogoPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CatalogoDTO]
