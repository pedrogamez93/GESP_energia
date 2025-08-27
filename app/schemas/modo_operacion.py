# app/schemas/modo_operacion.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class ModoOperacionSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config: from_attributes = True

class ModoOperacionDTO(ModoOperacionSelectDTO):
    Active: Optional[bool] = True

class ModoOperacionCreate(BaseModel):
    Nombre: Optional[str] = None

class ModoOperacionUpdate(BaseModel):
    Nombre: Optional[str] = None
    Active: Optional[bool] = None
