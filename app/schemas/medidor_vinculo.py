from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional

class IdsPayload(BaseModel):
    Ids: List[int] = []

# DTO minimal para listados rápidos (evitamos dependencia circular con schemas/medidor)
class MedidorMiniDTO(BaseModel):
    Id: int
    Numero: Optional[str] = None
    NumeroClienteId: Optional[int] = None
    DivisionId: Optional[int] = None  # por si la tabla Medidores también lo trae

    class Config:
        from_attributes = True
