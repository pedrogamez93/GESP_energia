from typing import List, Optional
from pydantic import BaseModel

from app.schemas.region import RegionDTO
from app.schemas.comuna import ComunaDTO

class ProvinciaBase(BaseModel):
    RegionId: int
    Nombre: str

class ProvinciaDTO(BaseModel):
    Id: int
    RegionId: int
    Nombre: str

    class Config:
        orm_mode = True
