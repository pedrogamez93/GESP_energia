from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class MedidorToDDL(BaseModel):
    Id: int
    Numero: str
    class Config:
        from_attributes = True

class MedidorLightDTO(BaseModel):
    Id: int
    Numero: str
    NumeroClienteId: int
    DivisionId: Optional[int] = None
    class Config:
        from_attributes = True

class MedidorParametrosModel(BaseModel):
    NumeroClienteId: int
    Numero: str
    DivisionId: Optional[int] = None
