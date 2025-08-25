from pydantic import BaseModel
from typing import Optional

# ---- Salidas ----
class UnidadMedidaDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    Abrv: Optional[str] = None
    class Config:
        from_attributes = True  # pydantic v2

class UnidadMedidaSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config:
        from_attributes = True  # pydantic v2

# ---- Entradas ----
class UnidadMedidaCreate(BaseModel):
    Nombre: Optional[str] = None
    Abrv: Optional[str] = None

class UnidadMedidaUpdate(BaseModel):
    Nombre: Optional[str] = None
    Abrv: Optional[str] = None
