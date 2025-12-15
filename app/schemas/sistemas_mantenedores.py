# app/schemas/sistemas_mantenedores.py
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class SimpleCatalogDTO(BaseModel):
    """
    Item genérico de catálogo: Id, Nombre (+ Active opcional).
    Se usa para equipos, energéticos y colectores.
    """
    model_config = ConfigDict(from_attributes=True)

    Id: int
    Nombre: str
    Active: Optional[bool] = None


class CompatEquipoEnergeticoDTO(BaseModel):
    """
    Relación Equipo ↔ Energético.
    """
    model_config = ConfigDict(from_attributes=True)

    Id: int
    TipoEquipoCalefaccionId: int
    EnergeticoId: int


class RefrigeracionCatalogosDTO(BaseModel):
    """
    Payload de catálogos para el mantenedor de Refrigeración.
    """
    equipos: List[SimpleCatalogDTO]
    energeticos: List[SimpleCatalogDTO]
    compatibilidades: List[CompatEquipoEnergeticoDTO]
    temperaturas: List[int]


class ACSCatalogosDTO(BaseModel):
    """
    Payload de catálogos para el mantenedor de ACS.
    """
    equipos: List[SimpleCatalogDTO]
    energeticos: List[SimpleCatalogDTO]
    compatibilidades: List[CompatEquipoEnergeticoDTO]
    colectores: List[SimpleCatalogDTO]


# ------------------ DTOs de entrada (crear / editar) ------------------


class EquipoBaseIn(BaseModel):
    nombre: str
    codigo: Optional[str] = None
    active: bool = True


class EquipoUpdateIn(BaseModel):
    nombre: Optional[str] = None
    codigo: Optional[str] = None
    active: Optional[bool] = None


class EquipoRefrigeracionCreate(EquipoBaseIn):
    """Crear equipo de Refrigeración (se marcará con FR = true en el modelo)."""
    pass


class EquipoRefrigeracionUpdate(EquipoUpdateIn):
    """Editar equipo de Refrigeración."""
    pass


class EquipoACSCreate(EquipoBaseIn):
    """Crear equipo de ACS (se marcará con AC = true en el modelo)."""
    pass


class EquipoACSUpdate(EquipoUpdateIn):
    """Editar equipo de ACS."""
    pass


class CompatEnergeticoCreate(BaseModel):
    """
    Crear compatibilidad entre equipo y energético.
    Sirve tanto para Refrigeración como para ACS.
    """
    tipo_equipo_calefaccion_id: int
    energetico_id: int
