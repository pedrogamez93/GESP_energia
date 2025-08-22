# app/schemas/institucion.py
from typing import Optional
from pydantic import BaseModel, ConfigDict

# --- Salidas ---

class InstitucionListDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)  # pydantic v2


class InstitucionDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    Active: bool
    model_config = ConfigDict(from_attributes=True)  # pydantic v2


# --- Entradas ---

class InstitucionCreate(BaseModel):
    # En la app original, crear sólo pide Nombre
    Nombre: str


class InstitucionUpdate(BaseModel):
    # Ahora permite editar Nombre y Active (para activar/desactivar)
    Nombre: Optional[str] = None
    Active: Optional[bool] = None
