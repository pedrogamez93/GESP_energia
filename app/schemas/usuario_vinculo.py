from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class IdsPayload(BaseModel):
    Ids: List[int] = []


class UserDetailDTO(BaseModel):
    """DTO compacto (el que tenías)."""
    Id: str
    UserName: str | None = None
    Email: str | None = None
    Active: bool | None = None
    Roles: List[str] = []
    InstitucionIds: List[int] = []
    ServicioIds: List[int] = []
    DivisionIds: List[int] = []
    UnidadIds: List[int] = []

    model_config = ConfigDict(from_attributes=True)


class UserDetailFullDTO(BaseModel):
    """
    DTO completo con TODAS las columnas de dbo.AspNetUsers + sets/roles.
    Tipos alineados a SQL Server (bit->bool, datetime/datetimeoffset->datetime, nvarchar->str).
    """
    # ---- columnas de AspNetUsers ----
    AccessFailedCount: Optional[int] = None
    EmailConfirmed: Optional[bool] = None
    LockoutEnabled: Optional[bool] = None
    LockoutEnd: Optional[datetime] = None
    PhoneNumberConfirmed: Optional[bool] = None
    TwoFactorEnabled: Optional[bool] = None
    Id: str
    UserName: Optional[str] = None
    NormalizedUserName: Optional[str] = None
    Email: Optional[str] = None
    NormalizedEmail: Optional[str] = None
    PasswordHash: Optional[str] = None
    SecurityStamp: Optional[str] = None
    ConcurrencyStamp: Optional[str] = None
    PhoneNumber: Optional[str] = None
    Nombres: Optional[str] = None
    Apellidos: Optional[str] = None
    Active: Optional[bool] = None
    Address: Optional[str] = None
    City: Optional[str] = None
    PostalCode: Optional[str] = None
    Cargo: Optional[str] = None

    # IMPORTANTE: en tu BD este campo llega como bit -> bool
    Certificado: Optional[bool] = None

    Nacionalidad: Optional[str] = None
    Rut: Optional[str] = None

    # También suelen ser bit en tu esquema
    Validado: Optional[bool] = None

    OldId: Optional[str] = None
    ComunaId: Optional[int] = None
    SexoId: Optional[int] = None
    NumeroTelefonoOpcional: Optional[str] = None

    CreatedAt: Optional[datetime] = None
    CreatedBy: Optional[str] = None
    ModifiedBy: Optional[str] = None
    UpdatedAt: Optional[datetime] = None

    # ---- agregados del endpoint ----
    Roles: List[str] = Field(default_factory=list)
    InstitucionIds: List[int] = Field(default_factory=list)
    ServicioIds: List[int] = Field(default_factory=list)
    DivisionIds: List[int] = Field(default_factory=list)
    UnidadIds: List[int] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
