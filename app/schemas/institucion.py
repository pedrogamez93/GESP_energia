# app/schemas/institucion.py
from typing import Optional
from pydantic import BaseModel, ConfigDict

# --- Salidas ---

class InstitucionListDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    Active: bool
    model_config = ConfigDict(from_attributes=True)  # pydantic v2


class InstitucionDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    Active: bool
    model_config = ConfigDict(from_attributes=True)  # pydantic v2


# --- Entradas ---

class InstitucionCreate(BaseModel):
    Nombre: str


class InstitucionUpdate(BaseModel):
    Nombre: Optional[str] = None
    Active: Optional[bool] = None
