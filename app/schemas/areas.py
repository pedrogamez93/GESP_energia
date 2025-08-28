from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AreaListDTO(BaseModel):
    Id: int
    PisoId: int
    Nombre: str
    Superficie: Optional[float] = None
    Active: bool
    model_config = ConfigDict(from_attributes=True)

class AreaDTO(AreaListDTO):
    CreatedAt: datetime
    UpdatedAt: datetime
    Version: int
    TipoUsoId: Optional[int] = None
    Observaciones: Optional[str] = None
    Orden: Optional[int] = None

class AreaCreate(BaseModel):
    PisoId: int
    Nombre: str
    Superficie: Optional[float] = None
    TipoUsoId: Optional[int] = None
    Observaciones: Optional[str] = None
    Orden: Optional[int] = None

class AreaUpdate(BaseModel):
    PisoId: Optional[int] = None
    Nombre: Optional[str] = None
    Superficie: Optional[float] = None
    TipoUsoId: Optional[int] = None
    Observaciones: Optional[str] = None
    Orden: Optional[int] = None
    Active: Optional[bool] = None
