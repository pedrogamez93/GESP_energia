# app/schemas/numero_cliente.py
from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer


class NumeroClienteListDTO(BaseModel):
    Id: int
    Numero: Optional[str] = None
    NombreCliente: Optional[str] = None
    EmpresaDistribuidoraId: Optional[int] = None
    TipoTarifaId: Optional[int] = None
    DivisionId: Optional[int] = None
    PotenciaSuministrada: float = 0.0
    Active: bool = True

    # Pydantic v2: reemplaza orm_mode por from_attributes
    model_config = ConfigDict(from_attributes=True)


class NumeroClienteDTO(NumeroClienteListDTO):
    CreatedAt: Optional[datetime] = None
    UpdatedAt: Optional[datetime] = None
    Version: Optional[int] = None

    # Si prefieres strings ISO8601 en la respuesta, dejamos este serializer.
    # Además, normalizamos fechas mínimas (SQL Server 0001-01-01) a None.
    @field_serializer("CreatedAt", "UpdatedAt")
    def _serialize_dt(self, v: Optional[datetime], _info):
        if not v or v.year <= 1:
            return None
        return v.isoformat()


class NumeroClienteCreate(BaseModel):
    Numero: Optional[str] = None
    NombreCliente: Optional[str] = None
    EmpresaDistribuidoraId: Optional[int] = None
    TipoTarifaId: Optional[int] = None
    DivisionId: Optional[int] = None
    PotenciaSuministrada: float = 0.0


class NumeroClienteUpdate(BaseModel):
    Numero: Optional[str] = None
    NombreCliente: Optional[str] = None
    EmpresaDistribuidoraId: Optional[int] = None
    TipoTarifaId: Optional[int] = None
    DivisionId: Optional[int] = None
    PotenciaSuministrada: Optional[float] = None
    Active: Optional[bool] = None
