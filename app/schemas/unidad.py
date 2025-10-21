# app/schemas/unidad.py
from __future__ import annotations
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, ConfigDict

# ───────────────────────────────────────────────────────────────────────────────
# Objetos base anidados usados por Unidad
# ───────────────────────────────────────────────────────────────────────────────

class ServicioDTO(BaseModel):
    Id: int
    Nombre: str
    model_config = ConfigDict(from_attributes=True)


class InmuebleTopDTO(BaseModel):
    Id: int
    TipoInmueble: int
    Calle: Optional[str] = None
    Numero: Optional[str] = None
    Comuna: Optional[str] = None
    Region: Optional[str] = None
    Nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class pisoDTO(BaseModel):  # (sic) nombre tal cual en .NET
    Id: int
    NumeroPisoNombre: Optional[str] = None
    Checked: bool
    model_config = ConfigDict(from_attributes=True)


class AreaDTO(BaseModel):
    # OJO: 'Nomnbre' viene con typo en el DTO C# y lo mantenemos por compatibilidad
    Id: int
    Nomnbre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class UnidadInmuebleDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ───────────────────────────────────────────────────────────────────────────────
# DTOs principales de Unidad
# ───────────────────────────────────────────────────────────────────────────────

class UnidadDTO(BaseModel):
    Id: int
    OldId: Optional[int] = None
    Nombre: str
    ServicioId: int
    ServicioNombre: Optional[str] = None
    InstitucionNombre: Optional[str] = None
    Active: Optional[str] = None
    Funcionarios: int
    ReportaPMG: bool
    IndicadorEE: bool
    AccesoFactura: int
    InstitucionResponsableId: Optional[int] = None
    ServicioResponsableId: Optional[int] = None
    OrganizacionResponsable: Optional[str] = None

    Servicio: Optional[ServicioDTO] = None
    Inmuebles: List[InmuebleTopDTO] = []
    Pisos: List[pisoDTO] = []
    Areas: List[AreaDTO] = []

    model_config = ConfigDict(from_attributes=True)


class UnidadListDTO(BaseModel):
    Id: int
    OldId: Optional[int] = None
    Nombre: str
    Ubicacion: Optional[str] = None

    InstitucionId: int
    InstitucionNombre: str

    ServicioId: int
    ServicioNombre: str

    Active: Optional[str] = None
    Funcionarios: int
    ReportaPMG: bool
    IndicadorEE: bool

    # Nota: en .NET aparece como string; mantenemos ese contrato
    AccesoFactura: Optional[str] = None

    InstitucionResponsableId: Optional[int] = None
    InstitucionResponsableNombre: Optional[str] = None
    ServicioResponsableId: Optional[int] = None
    ServicioResponsableNombre: Optional[str] = None
    OrganizacionResponsable: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UnidadFilterDTO(BaseModel):
    Unidad: Optional[str] = None
    userId: Optional[str] = None
    InstitucionId: Optional[int] = None
    ServicioId: Optional[int] = None
    RegionId: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class UnidadPatchDTO(BaseModel):
    Nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class UnidadReporteConsumoDTO(BaseModel):
    Id: int
    Direccion: Optional[str] = None
    AccesoFactura: int
    ServicioResponsableId: int
    Compromiso2022: Optional[bool] = None
    EstadoCompromiso2022: Optional[int] = None
    Justificacion: Optional[str] = None
    ObservacionCompromiso2022: Optional[str] = None

    # Campo calculado en C#: lo exponemos como propiedad normal
    EstadoJustificacion: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ───────────────────────────────────────────────────────────────────────────────
# Wrapper de paginación reutilizable
# ───────────────────────────────────────────────────────────────────────────────

T = TypeVar("T")

class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int

class Page(Generic[T], BaseModel):
    data: List[T]
    meta: PageMeta
