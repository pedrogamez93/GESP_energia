# app/schemas/sistemas_mantenedores.py
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class CatalogItem(BaseModel):
    Id: int
    Nombre: str
    Active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class CatalogItemWithExtra(CatalogItem):
    Codigo: Optional[str] = None
    Tipo: Optional[str] = None


class CompatEquipoEnergetico(BaseModel):
    Id: int
    TipoEquipoCalefaccionId: int
    EnergeticoId: int

    model_config = ConfigDict(from_attributes=True)


class RefrigeracionCatalogosDTO(BaseModel):
    equiposRefrigeracion: List[CatalogItemWithExtra]
    energeticos: List[CatalogItem]
    compatibilidades: List[CompatEquipoEnergetico]
    temperaturasSeteo: List[int]


class ACSCatalogosDTO(BaseModel):
    equiposAcs: List[CatalogItemWithExtra]
    energeticos: List[CatalogItem]
    compatibilidades: List[CompatEquipoEnergetico]
    tiposColectores: List[CatalogItemWithExtra]
