from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel

class EnergeticoDivisionDTO(BaseModel):
    Id: int
    DivisionId: int
    EnergeticoId: int
    NumeroClienteId: Optional[int] = None
    class Config: from_attributes = True

class EnergeticoDivisionCreateItem(BaseModel):
    EnergeticoId: int
    NumeroClienteId: Optional[int] = None

class EnergeticoDivisionReplacePayload(BaseModel):
    items: List[EnergeticoDivisionCreateItem] = []
