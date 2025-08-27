from __future__ import annotations
from typing import List
from pydantic import BaseModel

class MedidorDivisionDTO(BaseModel):
    Id: int
    DivisionId: int
    MedidorId: int
    class Config: from_attributes = True

class IdsPayload(BaseModel):
    Ids: List[int] = []
