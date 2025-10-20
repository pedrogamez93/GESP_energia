from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

# --- Select ligero (compatibilidad con sistemas.py) ---
class CatalogoSelectDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: int
    Nombre: Optional[str] = None

# --- DTO completo de catálogo genérico ---
class CatalogoDTO(CatalogoSelectDTO):
    Active: Optional[bool] = True

# --- Payloads CRUD ---
class CatalogoCreate(BaseModel):
    Nombre: Optional[str] = None

class CatalogoUpdate(BaseModel):
    Nombre: Optional[str] = None
    Active: Optional[bool] = None

# --- Página estándar (para listados paginados) ---
class CatalogoPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CatalogoDTO]
