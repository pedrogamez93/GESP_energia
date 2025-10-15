from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class DivisionSistemasDTO(BaseModel):
    # Identificador
    DivisionId: int

    # Iluminación
    TipoLuminariaId: Optional[int] = None

    # Calefacción
    EquipoCalefaccionId: Optional[int] = None
    EnergeticoCalefaccionId: Optional[int] = None
    TempSeteoCalefaccionId: Optional[int] = None

    # Refrigeración
    EquipoRefrigeracionId: Optional[int] = None
    EnergeticoRefrigeracionId: Optional[int] = None
    TempSeteoRefrigeracionId: Optional[int] = None

    # ACS
    EquipoAcsId: Optional[int] = None
    EnergeticoAcsId: Optional[int] = None
    SistemaSolarTermico: Optional[bool] = None
    ColectorId: Optional[int] = None
    SupColectores: Optional[float] = None
    FotoTecho: Optional[bool] = None
    SupFotoTecho: Optional[float] = None
    InstTerSisFv: Optional[bool] = None
    SupInstTerSisFv: Optional[float] = None
    ImpSisFv: Optional[bool] = None
    SupImptSisFv: Optional[float] = None
    PotIns: Optional[float] = None
    MantColectores: Optional[int] = None
    MantSfv: Optional[int] = None

    Version: Optional[int] = None


class DivisionSistemasUpdate(BaseModel):
    # Todos opcionales para permitir updates parciales (PATCH-like)
    TipoLuminariaId: Optional[int] = None

    EquipoCalefaccionId: Optional[int] = None
    EnergeticoCalefaccionId: Optional[int] = None
    TempSeteoCalefaccionId: Optional[int] = None

    EquipoRefrigeracionId: Optional[int] = None
    EnergeticoRefrigeracionId: Optional[int] = None
    TempSeteoRefrigeracionId: Optional[int] = None

    EquipoAcsId: Optional[int] = None
    EnergeticoAcsId: Optional[int] = None
    SistemaSolarTermico: Optional[bool] = None
    ColectorId: Optional[int] = None
    SupColectores: Optional[float] = None
    FotoTecho: Optional[bool] = None
    SupFotoTecho: Optional[float] = None
    InstTerSisFv: Optional[bool] = None
    SupInstTerSisFv: Optional[float] = None
    ImpSisFv: Optional[bool] = None
    SupImptSisFv: Optional[float] = None
    PotIns: Optional[float] = None
    MantColectores: Optional[int] = None
    MantSfv: Optional[int] = None
