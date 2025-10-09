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

    # Pydantic v2: habilita lectura desde ORM/SA
    model_config = ConfigDict(from_attributes=True)


class MedidorDTO(MedidorListDTO):
    # 🔧 Cambio clave: usar datetime en vez de str para que no falle la validación
    CreatedAt: Optional[datetime] = None
    UpdatedAt: Optional[datetime] = None
    Version: Optional[int] = None

    # Serializa a ISO-8601 en JSON (por si el frontend espera string)
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


# Página tipada para Swagger y validación
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
    # ❗️Evitar defaults mutables
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
