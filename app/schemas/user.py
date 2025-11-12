from __future__ import annotations

from typing import Optional, Union, Literal
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, AliasChoices, ConfigDict

# ─────────────────────────────────────────────────────────────────────────────
# Schemas de entrada
# ─────────────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    # Requeridos mínimos (retrocompatible)
    email: EmailStr
    password: str
    full_name: Optional[str] = None  # si llega, se parte en Nombres/Apellidos si el modelo no tiene FullName

    # Extras opcionales mapeados a AspNetUsers (todos opcionales)
    Nombres: Optional[str] = None
    Apellidos: Optional[str] = None
    PhoneNumber: Optional[str] = None
    NumeroTelefonoOpcional: Optional[str] = None
    Address: Optional[str] = None
    City: Optional[str] = None
    PostalCode: Optional[str] = None
    Cargo: Optional[str] = None
    Nacionalidad: Optional[str] = None
    Rut: Optional[str] = None
    ComunaId: Optional[int] = None
    SexoId: Optional[int] = None
    Certificado: Optional[bool] = None
    Validado: Optional[bool] = None
    Active: Optional[bool] = True  # por defecto activo

class UserUpdate(BaseModel):
    # PUT completo (no toca email ni password por defecto)
    Nombres: Optional[str] = None
    Apellidos: Optional[str] = None
    full_name: Optional[str] = None
    PhoneNumber: Optional[str] = None
    NumeroTelefonoOpcional: Optional[str] = None
    Address: Optional[str] = None
    City: Optional[str] = None
    PostalCode: Optional[str] = None
    Cargo: Optional[str] = None
    Nacionalidad: Optional[str] = None
    Rut: Optional[str] = None
    ComunaId: Optional[int] = None
    SexoId: Optional[int] = None
    Certificado: Optional[bool] = None
    Validado: Optional[bool] = None
    Active: Optional[bool] = None

class UserPatch(UserUpdate):
    # Igual que update, pero semánticamente PATCH
    pass

class ChangePassword(BaseModel):
    new_password: str

# ─────────────────────────────────────────────────────────────────────────────
# Schemas de salida
# ─────────────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    # Soporta Id/id (string o int)
    id: Union[int, str] = Field(validation_alias=AliasChoices("id", "Id"))
    email: EmailStr = Field(validation_alias=AliasChoices("email", "Email"))

    # nombre compuesto si existe o derivado de Nombres/Apellidos
    full_name: Optional[str] = Field(default=None, validation_alias=AliasChoices("FullName", "full_name"))

    # Campos relevantes del formulario
    Nombres: Optional[str] = None
    Apellidos: Optional[str] = None
    PhoneNumber: Optional[str] = None
    NumeroTelefonoOpcional: Optional[str] = None
    Address: Optional[str] = None
    City: Optional[str] = None
    PostalCode: Optional[str] = None
    Cargo: Optional[str] = None
    Nacionalidad: Optional[str] = None
    Rut: Optional[str] = None
    ComunaId: Optional[int] = None
    SexoId: Optional[int] = None
    Certificado: Optional[bool] = None
    Validado: Optional[bool] = None
    Active: Optional[bool] = True

    # Auditorio
    CreatedAt: Optional[datetime] = None
    UpdatedAt: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
