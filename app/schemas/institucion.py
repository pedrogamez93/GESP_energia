# app/schemas/institucion.py
from pydantic import BaseModel
from typing import Optional

# --- Salidas ---

class InstitucionListDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None

    class Config:
        from_attributes = True  # pydantic v2


class InstitucionDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    Active: bool

    class Config:
        from_attributes = True  # pydantic v2


# --- Entradas ---

class InstitucionCreate(BaseModel):
    # En la app original, crear sólo pide Nombre
    Nombre: str


class InstitucionUpdate(BaseModel):
    # Para editar, seguimos el mismo modelo: sólo Nombre
    Nombre: str
