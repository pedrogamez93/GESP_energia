# app/schemas/edificio.py
from pydantic import BaseModel
from typing import Optional

class EdificioSelectDTO(BaseModel):
    Id: int
    Nombre: str  # Etiqueta calculada (p. ej., "Calle 123" o "Direccion 123")
    class Config: from_attributes = True

class EdificioListDTO(BaseModel):
    Id: int
    Calle: Optional[str] = None
    Numero: Optional[str] = None
    Direccion: Optional[str] = None
    ComunaId: Optional[int] = None
    Active: Optional[bool] = True
    class Config: from_attributes = True

class EdificioDTO(EdificioListDTO):
    Latitud: Optional[float] = None
    Longitud: Optional[float] = None
    Altitud: Optional[float] = None
    TipoEdificioId: Optional[int] = None
    TipoAgrupamientoId: Optional[int] = None
    EntornoId: Optional[int] = None
    InerciaTermicaId: Optional[int] = None
    FrontisId: Optional[int] = None

class EdificioCreate(BaseModel):
    Direccion: Optional[str] = None
    Numero: Optional[str] = None
    Calle: Optional[str] = None
    ComunaId: Optional[int] = None
    Latitud: Optional[float] = None
    Longitud: Optional[float] = None
    Altitud: Optional[float] = None
    TipoEdificioId: Optional[int] = None
    TipoAgrupamientoId: Optional[int] = None
    EntornoId: Optional[int] = None
    InerciaTermicaId: Optional[int] = None
    FrontisId: Optional[int] = None

class EdificioUpdate(EdificioCreate):
    Active: Optional[bool] = None  # por si quieres activar/desactivar
