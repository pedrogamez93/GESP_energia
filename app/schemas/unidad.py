# app/schemas/unidad.py
from __future__ import annotations
from typing import List, Optional, Union, Any
from pydantic import BaseModel, ConfigDict


# --------- DTOs auxiliares que usa el servicio ---------

class InmuebleTopDTO(BaseModel):
    """Proyección mínima para mostrar Inmuebles asociados a una Unidad."""
    model_config = ConfigDict(from_attributes=True)

    Id: int
    TipoInmueble: Optional[int] = None


class pisoDTO(BaseModel):
    """Proyección mínima de Piso asociada a una Unidad."""
    model_config = ConfigDict(from_attributes=True)

    Id: int
    NumeroPisoNombre: Optional[str] = None
    Checked: Optional[bool] = None


class AreaDTO(BaseModel):
    """Proyección mínima de Área asociada a una Unidad."""
    model_config = ConfigDict(from_attributes=True)

    Id: int
    # ⚠️ OJO: el servicio usa 'Nombre' (no 'Nomnbre')
    Nombre: Optional[str] = None


# --------- Filtros / Patch ---------

class UnidadFilterDTO(BaseModel):
    """Filtro usado por list_filter en UnidadService."""
    model_config = ConfigDict(from_attributes=True)

    Unidad: Optional[str] = None
    userId: Optional[str] = None
    InstitucionId: Optional[int] = None
    ServicioId: Optional[int] = None
    RegionId: Optional[int] = None


class UnidadPatchDTO(BaseModel):
    """
    Placeholder para compatibilidad de imports (router).
    Ajusta campos si necesitas PATCH real.
    """
    model_config = ConfigDict(from_attributes=True)
    # Define aquí campos opcionales si luego implementas PATCH.


# --------- DTOs principales ---------

class UnidadDTO(BaseModel):
    """
    DTO de detalle de Unidad. Coincide con el mapeo que hace UnidadService._map_unidad_to_dto.
    """
    model_config = ConfigDict(from_attributes=True)

    Id: int
    OldId: Optional[int] = None
    Nombre: Optional[str] = None

    ServicioId: int
    ServicioNombre: Optional[str] = None
    InstitucionNombre: Optional[str] = None

    Active: Union[str, int]  # en tu service envías "1"/"0"
    Funcionarios: Optional[int] = 0
    ReportaPMG: bool = False
    IndicadorEE: bool = False
    AccesoFactura: Union[int, str] = 0  # a veces string en listDTO

    InstitucionResponsableId: Optional[int] = None
    ServicioResponsableId: Optional[int] = None
    OrganizacionResponsable: Optional[str] = None

    # Si en algún momento pasas un objeto Servicio real, puedes tiparlo mejor
    Servicio: Optional[Any] = None

    Inmuebles: List[InmuebleTopDTO] = []
    Pisos: List[pisoDTO] = []
    Areas: List[AreaDTO] = []


class UnidadListDTO(BaseModel):
    """
    DTO de listado de Unidades. Coincide con _map_unidad_to_listdto.
    """
    model_config = ConfigDict(from_attributes=True)

    Id: int
    OldId: Optional[int] = None
    Nombre: Optional[str] = None

    Ubicacion: Optional[str] = None

    InstitucionId: int
    InstitucionNombre: Optional[str] = ""
    ServicioId: int
    ServicioNombre: Optional[str] = ""

    Active: Union[str, int]
    Funcionarios: Optional[int] = 0
    ReportaPMG: bool = False
    IndicadorEE: bool = False
    AccesoFactura: Union[str, int] = "0"

    InstitucionResponsableId: Optional[int] = None
    InstitucionResponsableNombre: Optional[str] = None
    ServicioResponsableId: Optional[int] = None
    ServicioResponsableNombre: Optional[str] = None
    OrganizacionResponsable: Optional[str] = None


# Export explícito por claridad
__all__ = [
    "InmuebleTopDTO",
    "pisoDTO",
    "AreaDTO",
    "UnidadFilterDTO",
    "UnidadPatchDTO",
    "UnidadDTO",
    "UnidadListDTO",
]
