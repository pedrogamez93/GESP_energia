from pydantic import BaseModel

class ComunaDTO(BaseModel):
    Id: int
    ProvinciaId: int
    RegionId: int
    Nombre: str

    class Config:
        from_attributes = True