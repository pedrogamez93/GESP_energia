from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class DireccionDTO(BaseModel):
    Id: int
    Calle: Optional[str] = None
    Numero: Optional[str] = None
    DireccionCompleta: Optional[str] = None
    RegionId: Optional[int] = None
    ProvinciaId: Optional[int] = None
    ComunaId: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class DireccionCreate(BaseModel):
    Calle: Optional[str] = None
    Numero: Optional[str] = None
    DireccionCompleta: Optional[str] = None
    RegionId: Optional[int] = None
    ProvinciaId: Optional[int] = None
    ComunaId: Optional[int] = None

class DireccionUpdate(BaseModel):
    Calle: Optional[str] = None
    Numero: Optional[str] = None
    DireccionCompleta: Optional[str] = None
    RegionId: Optional[int] = None
    ProvinciaId: Optional[int] = None
    ComunaId: Optional[int] = None

class DireccionSearchResponse(BaseModel):
    Total: int
    Items: List[DireccionDTO]

class DireccionResolveRequest(BaseModel):
    Calle: str
    Numero: str
    ComunaId: int
