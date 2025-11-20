from __future__ import annotations
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer, Field, AliasChoices, field_validator


class IdsPayload(BaseModel):
    """
    Payload usado en:
      PUT /api/v1/usuarios/{user_id}/instituciones
      PUT /api/v1/usuarios/{user_id}/servicios
      PUT /api/v1/usuarios/{user_id}/divisiones
      PUT /api/v1/usuarios/{user_id}/unidades

    El front puede enviar:
      { "ids": [1, 2, 3] }
    o
      { "Ids": [1, 2, 3] }

    Internamente siempre trabajamos con el atributo `Ids`.
    """

    model_config = ConfigDict(
        populate_by_name=True,
    )

    # Acepta tanto "Ids" como "ids" en el JSON de entrada
    Ids: List[int] = Field(
        default_factory=list,
        validation_alias=AliasChoices("Ids", "ids"),
        serialization_alias="Ids",   # si quieres que al salir siempre se vea como "Ids"
    )

    @field_validator("Ids")
    @classmethod
    def _clean_ids(cls, v: List[int]) -> List[int]:
        """
        Normaliza la lista:
        - castea a int
        - filtra None y <= 0
        - elimina duplicados
        - ordena (solo para dejarlo más prolijo)
        """
        if not v:
            return []
        norm = {int(i) for i in v if i is not None and int(i) > 0}
        return sorted(norm)


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
    Roles: List[str] = Field(default_factory=list)
    InstitucionIds: List[int] = Field(default_factory=list)
    ServicioIds: List[int] = Field(default_factory=list)
    DivisionIds: List[int] = Field(default_factory=list)
    UnidadIds: List[int] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    # Serializadores para fechas (cuando salen a JSON)
    @field_serializer("LockoutEnd", "CreatedAt", "UpdatedAt", when_used="json")
    def _ser_dates(self, v: Optional[datetime], _info):
        return _ser_dt(v)
