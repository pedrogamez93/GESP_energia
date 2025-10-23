# app/schemas/area.py
from __future__ import annotations
from typing import Optional
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
    # Nota: Eliminado Observaciones y Orden porque NO existen en la tabla.
    # Si algún día se agregan a BD, los reponemos aquí.


class AreaCreate(BaseModel):
    PisoId: int
    Nombre: str
    Superficie: Optional[float] = None
    TipoUsoId: Optional[int] = None
    # Eliminados: Observaciones, Orden
    # Si necesitas NroRol al crear (existe en BD), puedes habilitarlo:
    # NroRol: Optional[int] = None


class AreaUpdate(BaseModel):
    PisoId: Optional[int] = None
    Nombre: Optional[str] = None
    Superficie: Optional[float] = None
    TipoUsoId: Optional[int] = None
    Active: Optional[bool] = None
    # Eliminados: Observaciones, Orden
    # Si vas a permitir actualizar NroRol:
    # NroRol: Optional[int] = None
