from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class ParametroMedicionDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config: from_attributes = True

class ParametroMedicionCreate(BaseModel):
    Nombre: str

class ParametroMedicionUpdate(BaseModel):
    Nombre: str
