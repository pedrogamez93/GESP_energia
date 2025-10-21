from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.direcciones import DireccionDTO


# ───────── Unidades (resumen para asociaciones) ─────────
class UnidadBriefDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ───────── Áreas / Pisos ─────────
class AreaDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    Active: bool = True
    Superficie: Optional[float] = None
    PisoId: Optional[int] = None
    Unidades: List[UnidadBriefDTO] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class PisoDTO(BaseModel):
    Id: int
    DivisionId: int
    PisoNumero: Optional[int] = None
    PisoNumeroNombre: Optional[str] = None  # NumeroPisos.Nombre
    Active: bool = True
    Areas: List[AreaDTO] = Field(default_factory=list)
    Unidades: List[UnidadBriefDTO] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


# ───────── Lecturas: lista y detalle ─────────
class InmuebleListDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    TipoInmueble: Optional[int] = None
    ParentId: Optional[int] = None
    ServicioId: Optional[int] = None
    Active: bool
    RegionId: Optional[int] = None
    ComunaId: Optional[int] = None
    Direccion: Optional[DireccionDTO] = None
    model_config = ConfigDict(from_attributes=True)


class InmuebleDTO(InmuebleListDTO):
    AnyoConstruccion: Optional[int] = None
    Superficie: Optional[float] = None
    NroRol: Optional[str] = None
    GeVersion: Optional[int] = None
    Children: List["InmuebleDTO"] = Field(default_factory=list)
    Pisos: List[PisoDTO] = Field(default_factory=list)
    Unidades: List[UnidadBriefDTO] = Field(default_factory=list)


class InmueblePage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[InmuebleListDTO]


# ───────── Escrituras ─────────
class InmuebleCreate(BaseModel):
    TipoInmueble: int
    Nombre: Optional[str] = None
    AnyoConstruccion: Optional[int] = None                 # opcional
    ServicioId: Optional[int] = None                       # si falta se hereda del padre
    TipoPropiedadId: int
    EdificioId: int
    Superficie: Optional[float] = None
    TipoUsoId: Optional[int] = None
    TipoAdministracionId: Optional[int] = None
    AdministracionServicioId: Optional[int] = None
    ParentId: Optional[int] = None
    NroRol: Optional[str] = None
    Direccion: Optional[DireccionDTO] = None
    Funcionarios: Optional[int] = 0                        # default anti-NULL


class InmuebleUpdate(BaseModel):
    TipoInmueble: Optional[int] = None
    Nombre: Optional[str] = None
    AnyoConstruccion: Optional[int] = None
    ServicioId: Optional[int] = None
    TipoPropiedadId: Optional[int] = None
    EdificioId: Optional[int] = None
    Superficie: Optional[float] = None
    TipoUsoId: Optional[int] = None
    TipoAdministracionId: Optional[int] = None
    AdministracionServicioId: Optional[int] = None
    ParentId: Optional[int] = None
    NroRol: Optional[str] = None
    Direccion: Optional[DireccionDTO] = None
    Active: Optional[bool] = None
    Funcionarios: Optional[int] = None


# ───────── Compat: búsquedas/vínculos ─────────
class InmuebleByAddressRequest(BaseModel):
    Calle: str
    Numero: str
    ComunaId: int


class InmuebleUnidadRequest(BaseModel):
    UnidadId: int = Field(..., gt=0)


class UnidadVinculadaDTO(BaseModel):
    UnidadId: int


# Pydantic v2: forward refs
InmuebleDTO.model_rebuild()
