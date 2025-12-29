from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TipoPropiedadDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    Orden: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)
