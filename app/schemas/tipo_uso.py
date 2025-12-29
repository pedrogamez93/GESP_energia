from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TipoUsoDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
