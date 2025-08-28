from __future__ import annotations
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict

# ---------- Lecturas ----------

class TareaDTO(BaseModel):
    Id: int
    CreatedAt: datetime
    UpdatedAt: datetime
    Version: int
    Active: bool

    ModifiedBy: Optional[str] = None
    CreatedBy: Optional[str] = None

    DimensionBrechaId: int
    AccionId: int

    Nombre: str
    FechaInicio: datetime
    FechaFin: datetime
    Responsable: str
    EstadoAvance: str
    Observaciones: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class TareaListDTO(BaseModel):
    Id: int
    Nombre: str
    FechaInicio: datetime
    FechaFin: datetime
    Responsable: str
    EstadoAvance: str
    AccionId: int
    DimensionBrechaId: int
    Active: bool
    model_config = ConfigDict(from_attributes=True)

class ResumenEstadoDTO(BaseModel):
    EstadoAvance: str
    Cantidad: int

# ---------- Escrituras ----------

class TareaCreate(BaseModel):
    DimensionBrechaId: int
    AccionId: int
    Nombre: str
    FechaInicio: datetime
    FechaFin: datetime
    Responsable: str
    EstadoAvance: str
    Observaciones: Optional[str] = None

class TareaUpdate(BaseModel):
    DimensionBrechaId: Optional[int] = None
    AccionId: Optional[int] = None
    Nombre: Optional[str] = None
    FechaInicio: Optional[datetime] = None
    FechaFin: Optional[datetime] = None
    Responsable: Optional[str] = None
    EstadoAvance: Optional[str] = None
    Observaciones: Optional[str] = None
    Active: Optional[bool] = None
