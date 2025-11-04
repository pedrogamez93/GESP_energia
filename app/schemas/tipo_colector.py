from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List

# ==== Select básico para grillas ====
class TipoColectorSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config: from_attributes = True

# ==== Detalle completo ====
class TipoColectorDTO(TipoColectorSelectDTO):
    Eta0: float
    A1: float
    A2: float
    AreaApertura: float
    Costo: float
    Costo_Mant: float
    VidaUtil: int
    Active: bool

# ==== Crear ====
class TipoColectorCreate(BaseModel):
    # el front suele mandar solo Nombre; el servicio completa con 0 / False
    Nombre: Optional[str] = None
    Eta0: float = 0
    A1: float = 0
    A2: float = 0
    AreaApertura: float = 0
    Costo: float = 0
    Costo_Mant: float = 0
    VidaUtil: int = 0
    Active: bool = True

# ==== Actualizar parcial (PATCH) ====
class TipoColectorUpdate(BaseModel):
    Nombre: Optional[str] = None
    Eta0: Optional[float] = None
    A1: Optional[float] = None
    A2: Optional[float] = None
    AreaApertura: Optional[float] = None
    Costo: Optional[float] = None
    Costo_Mant: Optional[float] = None
    VidaUtil: Optional[int] = None
    Active: Optional[bool] = None

# ==== Lista envoltorio para endpoints que devuelven colecciones ====
class TipoColectorListDTO(BaseModel):
    Items: List[TipoColectorDTO]
