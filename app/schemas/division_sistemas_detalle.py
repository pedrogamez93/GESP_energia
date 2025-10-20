from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


# ---------- Iluminación ----------
class IluminacionDTO(BaseModel):
    DivisionId: int
    TipoLuminariaId: Optional[int] = None
    Version: Optional[int] = None

class IluminacionUpdate(BaseModel):
    TipoLuminariaId: Optional[int] = None


# ---------- Calefacción ----------
class CalefaccionDTO(BaseModel):
    DivisionId: int
    EquipoCalefaccionId: Optional[int] = None
    EnergeticoCalefaccionId: Optional[int] = None
    TempSeteoCalefaccionId: Optional[int] = None  # 19|20|21|22
    Version: Optional[int] = None

class CalefaccionUpdate(BaseModel):
    EquipoCalefaccionId: Optional[int] = None
    EnergeticoCalefaccionId: Optional[int] = None
    TempSeteoCalefaccionId: Optional[int] = None


# ---------- Refrigeración ----------
class RefrigeracionDTO(BaseModel):
    DivisionId: int
    EquipoRefrigeracionId: Optional[int] = None
    EnergeticoRefrigeracionId: Optional[int] = None
    TempSeteoRefrigeracionId: Optional[int] = None  # 24
    Version: Optional[int] = None

class RefrigeracionUpdate(BaseModel):
    EquipoRefrigeracionId: Optional[int] = None
    EnergeticoRefrigeracionId: Optional[int] = None
    TempSeteoRefrigeracionId: Optional[int] = None


# ---------- ACS ----------
class ACSDTO(BaseModel):
    DivisionId: int
    EquipoAcsId: Optional[int] = None
    EnergeticoAcsId: Optional[int] = None
    SistemaSolarTermico: Optional[bool] = None
    ColectorId: Optional[int] = None
    SupColectores: Optional[float] = None
    MantColectores: Optional[int] = None
    Version: Optional[int] = None

class ACSUpdate(BaseModel):
    EquipoAcsId: Optional[int] = None
    EnergeticoAcsId: Optional[int] = None
    SistemaSolarTermico: Optional[bool] = None
    ColectorId: Optional[int] = None
    SupColectores: Optional[float] = None
    MantColectores: Optional[int] = None


# ---------- Fotovoltaico ----------
class FotovoltaicoDTO(BaseModel):
    DivisionId: int
    FotoTecho: Optional[bool] = None
    SupFotoTecho: Optional[float] = None
    InstTerSisFv: Optional[bool] = None
    SupInstTerSisFv: Optional[float] = None
    ImpSisFv: Optional[bool] = None
    SupImptSisFv: Optional[float] = None
    PotIns: Optional[float] = None
    MantSfv: Optional[int] = None
    Version: Optional[int] = None

class FotovoltaicoUpdate(BaseModel):
    FotoTecho: Optional[bool] = None
    SupFotoTecho: Optional[float] = None
    InstTerSisFv: Optional[bool] = None
    SupInstTerSisFv: Optional[float] = None
    ImpSisFv: Optional[bool] = None
    SupImptSisFv: Optional[float] = None
    PotIns: Optional[float] = None
    MantSfv: Optional[int] = None
