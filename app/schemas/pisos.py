from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class PisoListDTO(BaseModel):
    Id: int
    DivisionId: int
    Numero: Optional[str] = None
    Nombre: Optional[str] = None
    Superficie: Optional[float] = None
    Active: bool
    model_config = ConfigDict(from_attributes=True)

class PisoDTO(PisoListDTO):
    CreatedAt: datetime
    UpdatedAt: datetime
    Version: int
    Observaciones: Optional[str] = None
    Orden: Optional[int] = None

class PisoCreate(BaseModel):
    DivisionId: int
    Numero: Optional[str] = None
    Nombre: Optional[str] = None
    Superficie: Optional[float] = None
    Observaciones: Optional[str] = None
    Orden: Optional[int] = None

class PisoUpdate(BaseModel):
    DivisionId: Optional[int] = None
    Numero: Optional[str] = None
    Nombre: Optional[str] = None
    Superficie: Optional[float] = None
    Observaciones: Optional[str] = None
    Orden: Optional[int] = None
    Active: Optional[bool] = None
