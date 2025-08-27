from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class TipoTarifaDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config: from_attributes = True

class TipoTarifaCreate(BaseModel):
    Nombre: str

class TipoTarifaUpdate(BaseModel):
    Nombre: str
