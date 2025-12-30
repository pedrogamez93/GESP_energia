from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, field_serializer


# =========================
# Medidores (dbo.Medidores)
# =========================

class MedidorListDTO(BaseModel):
    Id: int
    Numero: Optional[str] = None
    NumeroClienteId: int
    Fases: int = 0
    Smart: bool = False
    Compartido: bool = False
    DivisionId: Optional[int] = None
    Factura: Optional[bool] = None
    Chilemedido: bool = False
    DeviceId: Optional[int] = None
    MedidorConsumo: bool = False
    Active: bool = True

    model_config = ConfigDict(from_attributes=True)


class MedidorDTO(MedidorListDTO):
    CreatedAt: Optional[datetime] = None
    UpdatedAt: Optional[datetime] = None
    Version: Optional[int] = None

    @field_serializer("CreatedAt", "UpdatedAt", when_used="json")
    def _ser_dt(self, v: Optional[datetime]):
        return v.isoformat() if v else None


class MedidorCreate(BaseModel):
    Numero: Optional[str] = None
    NumeroClienteId: int
    Fases: int = 0
    Smart: bool = False
    Compartido: bool = False
    DivisionId: Optional[int] = None
    Factura: Optional[bool] = None
    Chilemedido: bool = False
    DeviceId: Optional[int] = None
    MedidorConsumo: bool = False


class MedidorUpdate(BaseModel):
    Numero: Optional[str] = None
    NumeroClienteId: Optional[int] = None
    Fases: Optional[int] = None
    Smart: Optional[bool] = None
    Compartido: Optional[bool] = None
    DivisionId: Optional[int] = None
    Factura: Optional[bool] = None
    Chilemedido: Optional[bool] = None
    DeviceId: Optional[int] = None
    MedidorConsumo: Optional[bool] = None
    Active: Optional[bool] = None


class MedidorPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[MedidorListDTO]


# ======================================
# Medidores Inteligentes (dbo.MedidoresInteligentes)
# ======================================

class MedidorInteligenteDTO(BaseModel):
    Id: int
    ChileMedidoId: int
    DivisionIds: List[int] = Field(default_factory=list)
    EdificioIds: List[int] = Field(default_factory=list)
    ServicioIds: List[int] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MedidorInteligenteCreate(BaseModel):
    ChileMedidoId: int
    DivisionIds: List[int] = Field(default_factory=list)
    EdificioIds: List[int] = Field(default_factory=list)
    ServicioIds: List[int] = Field(default_factory=list)


class MedidorInteligenteUpdate(BaseModel):
    ChileMedidoId: Optional[int] = None
    Active: Optional[bool] = None
    DivisionIds: Optional[List[int]] = None
    EdificioIds: Optional[List[int]] = None
    ServicioIds: Optional[List[int]] = None


class IdsPayload(BaseModel):
    Ids: List[int] = Field(default_factory=list)


# ==========================================================
# ✅ NUEVO: DTOs para "detalle completo" y búsquedas jerárquicas
# ==========================================================

class InstitucionMiniDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None


class ServicioMiniDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    InstitucionId: Optional[int] = None


class DivisionMiniDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    ServicioId: Optional[int] = None
    DireccionId: Optional[int] = None


class DireccionMiniDTO(BaseModel):
    Id: int
    Calle: Optional[str] = None
    Numero: Optional[str] = None
    ComunaId: Optional[int] = None
    ProvinciaId: Optional[int] = None
    RegionId: Optional[int] = None
    Latitud: Optional[float] = None
    Longitud: Optional[float] = None


class MedidorDetalleDTO(BaseModel):
    Medidor: MedidorDTO
    Division: Optional[DivisionMiniDTO] = None
    Servicio: Optional[ServicioMiniDTO] = None
    Institucion: Optional[InstitucionMiniDTO] = None
    Direccion: Optional[DireccionMiniDTO] = None


class ServicioConMedidoresDTO(BaseModel):
    Servicio: ServicioMiniDTO
    Medidores: List[MedidorListDTO] = Field(default_factory=list)

# ==========================================================
# ✅ NUEVO: DTOs
# ==========================================================

class MedidorDetalleDTO(BaseModel):
    # Medidor
    Id: int
    Numero: Optional[str]
    Active: bool
    Fases: int
    Smart: bool
    Compartido: bool
    Chilemedido: bool

    # División
    DivisionId: Optional[int]
    DivisionNombre: Optional[str]

    # Servicio
    ServicioId: Optional[int]
    ServicioNombre: Optional[str]

    # Institución
    InstitucionId: Optional[int]
    InstitucionNombre: Optional[str]

    # Dirección (puede venir de divisiones o edificios)
    DireccionCompleta: Optional[str]
    RegionId: Optional[int]
    ProvinciaId: Optional[int]
    ComunaId: Optional[int]

    # Edificio (opcional)
    EdificioId: Optional[int]
    EdificioDireccion: Optional[str]

    model_config = ConfigDict(from_attributes=False)