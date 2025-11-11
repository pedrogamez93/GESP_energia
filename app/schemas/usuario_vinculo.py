from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_serializer

class IdsPayload(BaseModel):
    Ids: List[int] = []

def _ser_dt(v: Optional[datetime]) -> Optional[str]:
    if v is None:
        return None
    # ISO sin microsegundos
    return v.replace(microsecond=0).isoformat()

class UserDetailFullDTO(BaseModel):
    # ====== columnas AspNetUsers ======
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
    Certificado: Optional[bool] = None
    Nacionalidad: Optional[str] = None
    Rut: Optional[str] = None
    Validado: Optional[bool] = None
    OldId: Optional[int] = None
    ComunaId: Optional[int] = None
    SexoId: Optional[int] = None
    NumeroTelefonoOpcional: Optional[str] = None
    CreatedAt: Optional[datetime] = None
    CreatedBy: Optional[str] = None
    ModifiedBy: Optional[str] = None
    UpdatedAt: Optional[datetime] = None

    # ====== agregados (sets vinculados) ======
    Roles: List[str] = []
    InstitucionIds: List[int] = []
    ServicioIds: List[int] = []
    DivisionIds: List[int] = []
    UnidadIds: List[int] = []

    model_config = ConfigDict(from_attributes=True)

    # Serializadores para fechas (cuando salen a JSON)
    @field_serializer("LockoutEnd", "CreatedAt", "UpdatedAt", when_used="json")
    def _ser_dates(self, v: Optional[datetime], _info):
        return _ser_dt(v)
