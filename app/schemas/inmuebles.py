# app/schemas/inmuebles.py
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

# -------- Dirección --------
class DireccionDTO(BaseModel):
    Calle: Optional[str] = None
    Numero: Optional[str] = None
    RegionId: Optional[int] = None
    ProvinciaId: Optional[int] = None
    ComunaId: Optional[int] = None
    DireccionCompleta: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# -------- Lecturas --------
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

# -------- Escrituras --------
class InmuebleCreate(BaseModel):
    # obligatorios mínimos (ajustados al DDL de Divisiones)
    TipoInmueble: int
    Nombre: Optional[str] = None
    AnyoConstruccion: int
    ServicioId: int
    TipoPropiedadId: int
    EdificioId: int  # se usa en Divisiones
    # opcionales
    Superficie: Optional[float] = None
    TipoUsoId: Optional[int] = None
    TipoAdministracionId: Optional[int] = None
    AdministracionServicioId: Optional[int] = None
    ParentId: Optional[int] = None
    NroRol: Optional[str] = None
    Direccion: Optional[DireccionDTO] = None

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

# -------- Compat: búsquedas/vínculos (como .NET) --------
class InmuebleByAddressRequest(BaseModel):
    Calle: str
    Numero: str
    ComunaId: int

class InmuebleUnidadRequest(BaseModel):
    UnidadId: int


class UnidadVinculadaDTO(BaseModel):
    UnidadId: int