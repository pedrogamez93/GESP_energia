# app/schemas/tipo_equipo_calefaccion.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List

class TipoEquipoCalefaccionSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config: from_attributes = True

class TipoEquipoCalefaccionDTO(TipoEquipoCalefaccionSelectDTO):
    Rendimiento: float
    A: float
    B: float
    C: float
    Temp: float
    Costo: float
    Costo_Social: float
    Costo_Mant: float
    Costo_Social_Mant: float
    Ejec_HD_Maestro: float
    Ejec_HD_Ayte: float
    Ejec_HD_Jornal: float
    Mant_HD_Maestro: float
    Mant_HD_Ayte: float
    Mant_HD_Jornal: float
    AC: bool
    CA: bool
    FR: bool

class TipoEquipoCalefaccionCreate(BaseModel):
    Nombre: Optional[str] = None
    Rendimiento: float
    A: float
    B: float
    C: float
    Temp: float
    Costo: float
    Costo_Social: float
    Costo_Mant: float
    Costo_Social_Mant: float
    Ejec_HD_Maestro: float
    Ejec_HD_Ayte: float
    Ejec_HD_Jornal: float
    Mant_HD_Maestro: float
    Mant_HD_Ayte: float
    Mant_HD_Jornal: float
    AC: bool = False
    CA: bool = False
    FR: bool = False

class TipoEquipoCalefaccionUpdate(BaseModel):
    Nombre: Optional[str] = None
    Rendimiento: Optional[float] = None
    A: Optional[float] = None
    B: Optional[float] = None
    C: Optional[float] = None
    Temp: Optional[float] = None
    Costo: Optional[float] = None
    Costo_Social: Optional[float] = None
    Costo_Mant: Optional[float] = None
    Costo_Social_Mant: Optional[float] = None
    Ejec_HD_Maestro: Optional[float] = None
    Ejec_HD_Ayte: Optional[float] = None
    Ejec_HD_Jornal: Optional[float] = None
    Mant_HD_Maestro: Optional[float] = None
    Mant_HD_Ayte: Optional[float] = None
    Mant_HD_Jornal: Optional[float] = None
    AC: Optional[bool] = None
    CA: Optional[bool] = None
    FR: Optional[bool] = None

# N:M con energéticos
class TECEnergeticoDTO(BaseModel):
    Id: int
    TipoEquipoCalefaccionId: int
    EnergeticoId: int
    class Config: from_attributes = True

class TECEnergeticoCreate(BaseModel):
    EnergeticoId: int

class TECEnergeticoListDTO(BaseModel):
    Items: List[TECEnergeticoDTO]
