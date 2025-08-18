# app/schemas/region.py
from pydantic import BaseModel

class RegionDTO(BaseModel):
    Id: int
    Nombre: str
    Numero: int | None = None
    Posicion: int | None = None

    class Config:
        from_attributes = True