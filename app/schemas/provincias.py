from typing import List, Optional
from pydantic import BaseModel

from app.schemas.region import RegionDTO
from app.schemas.comuna import ComunaDTO

class ProvinciaBase(BaseModel):
    RegionId: int
    Nombre: str

class ProvinciaDTO(ProvinciaBase):
    Id: int
    Region: Optional[RegionDTO] = None
    Comunas: List[ComunaDTO] = []

    class Config:
        orm_mode = True
