# app/schemas/tipo_luminaria.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class TipoLuminariaSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config: from_attributes = True

class TipoLuminariaDTO(TipoLuminariaSelectDTO):
    Q_Educacion: float
    Q_Oficinas: float
    Q_Salud: float
    Q_Seguridad: float
    Area_Educacion: float
    Area_Oficinas: float
    Area_Salud: float
    Area_Seguridad: float
    Vida_Util: int
    Costo_Lamp: int
    Costo_Lum: int
    Costo_Social_Lamp: int
    Costo_Social_Lum: int
    Ejec_HD_Maestro: float
    Ejec_HD_Ayte: float
    Ejec_HD_Jornal: float
    Rep_HD_Maestro: float
    Rep_HD_Ayte: float
    Rep_HD_Jornal: float

class TipoLuminariaCreate(BaseModel):
    Nombre: Optional[str] = None
    Q_Educacion: float
    Q_Oficinas: float
    Q_Salud: float
    Q_Seguridad: float
    Area_Educacion: float
    Area_Oficinas: float
    Area_Salud: float
    Area_Seguridad: float
    Vida_Util: int
    Costo_Lamp: int
    Costo_Lum: int
    Costo_Social_Lamp: int
    Costo_Social_Lum: int
    Ejec_HD_Maestro: float
    Ejec_HD_Ayte: float
    Ejec_HD_Jornal: float
    Rep_HD_Maestro: float
    Rep_HD_Ayte: float
    Rep_HD_Jornal: float

class TipoLuminariaUpdate(BaseModel):
    Nombre: Optional[str] = None
    Q_Educacion: Optional[float] = None
    Q_Oficinas: Optional[float] = None
    Q_Salud: Optional[float] = None
    Q_Seguridad: Optional[float] = None
    Area_Educacion: Optional[float] = None
    Area_Oficinas: Optional[float] = None
    Area_Salud: Optional[float] = None
    Area_Seguridad: Optional[float] = None
    Vida_Util: Optional[int] = None
    Costo_Lamp: Optional[int] = None
    Costo_Lum: Optional[int] = None
    Costo_Social_Lamp: Optional[int] = None
    Costo_Social_Lum: Optional[int] = None
    Ejec_HD_Maestro: Optional[float] = None
    Ejec_HD_Ayte: Optional[float] = None
    Ejec_HD_Jornal: Optional[float] = None
    Rep_HD_Maestro: Optional[float] = None
    Rep_HD_Ayte: Optional[float] = None
    Rep_HD_Jornal: Optional[float] = None
