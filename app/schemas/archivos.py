from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class TipoArchivoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: int
    Extension: str
    MimeType: str
    FormatoFactura: bool

class ArchivoAdjuntoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: int
    Nombre: str
    Url: str
    MimeType: str
    ext: str
    DivisionId: int
    TipoArchivoId: Optional[int] = None
    CompraId: Optional[int] = None
    CreatedAt: datetime
    UpdatedAt: Optional[datetime] = None
    Active: bool
    Version: int

class ArchivoAdjuntoForRegister(BaseModel):
    DivisionId: int
    CompraId: Optional[int] = None
    # estos 3 se completan en server al subir archivo
    Nombre: Optional[str] = None
    Url: Optional[str] = None
    ext: Optional[str] = None

class ArchivoAdjuntoForEdit(BaseModel):
    Id: int
    DivisionId: int
    CompraId: Optional[int] = None
    Nombre: str
    Url: str
    ext: str
