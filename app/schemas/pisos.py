# app/schemas/pisos.py
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class PisoListDTO(BaseModel):
    Id: int
    # Algunos registros pueden venir con DivisionId = NULL en BD → hacerlo opcional en lecturas
    DivisionId: Optional[int] = None
    Numero: Optional[str] = None
    Nombre: Optional[str] = None
    Superficie: Optional[float] = None
    # Tolerar Active NULL en BD; si prefieres, puedes dejarlo como bool = True
    Active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

class PisoDTO(PisoListDTO):
    CreatedAt: datetime
    UpdatedAt: datetime
    Version: int
    Observaciones: Optional[str] = None
    Orden: Optional[int] = None

class PisoCreate(BaseModel):
    # En creación lo mantenemos requerido (normalmente la BD lo exige)
    DivisionId: int
    Numero: Optional[str] = None
    Nombre: Optional[str] = None
    Superficie: Optional[float] = None
    Observaciones: Optional[str] = None
    Orden: Optional[int] = None

class PisoUpdate(BaseModel):
    # En update es opcional
    DivisionId: Optional[int] = None
    Numero: Optional[str] = None
    Nombre: Optional[str] = None
    Superficie: Optional[float] = None
    Observaciones: Optional[str] = None
    Orden: Optional[int] = None
    Active: Optional[bool] = None
