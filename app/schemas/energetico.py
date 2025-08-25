from pydantic import BaseModel, Field
from typing import Optional, List

# --- Básicos ---
class EnergeticoDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    Icono: Optional[str] = None
    Multiple: bool
    PermiteMedidor: bool
    Posicion: int
    PermitePotenciaSuministrada: bool
    PermiteTipoTarifa: bool
    Active: bool = True
    class Config: from_attributes = True

class EnergeticoListDTO(EnergeticoDTO):
    pass

class EnergeticoSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config: from_attributes = True

class EnergeticoCreate(BaseModel):
    Nombre: Optional[str] = None
    Icono: Optional[str] = None
    Multiple: bool = False
    PermiteMedidor: bool = False
    Posicion: int = 0
    PermitePotenciaSuministrada: bool = False
    PermiteTipoTarifa: bool = False

class EnergeticoUpdate(BaseModel):
    Nombre: Optional[str] = None
    Icono: Optional[str] = None
    Multiple: Optional[bool] = None
    PermiteMedidor: Optional[bool] = None
    Posicion: Optional[int] = None
    PermitePotenciaSuministrada: Optional[bool] = None
    PermiteTipoTarifa: Optional[bool] = None
    Active: Optional[bool] = None

# --- Unidades por energético (N:M con metadata) ---
class EnergeticoUMDTO(BaseModel):
    Id: int
    Calor: float
    Densidad: float
    Factor: float
    EnergeticoId: int
    UnidadMedidaId: int
    Active: bool = True
    class Config: from_attributes = True

class EnergeticoUMCreate(BaseModel):
    Calor: float
    Densidad: float
    Factor: float
    UnidadMedidaId: int

class EnergeticoUMUpdate(BaseModel):
    Calor: Optional[float] = None
    Densidad: Optional[float] = None
    Factor: Optional[float] = None
    Active: Optional[bool] = None

# --- Energetico por División ---
class EnergeticoDivisionDTO(BaseModel):
    Id: int
    DivisionId: int
    EnergeticoId: int
    NumeroClienteId: Optional[int] = None
    Active: bool = True
    class Config: from_attributes = True

class EnergeticoDivisionCreate(BaseModel):
    DivisionId: int
    EnergeticoId: int
    NumeroClienteId: Optional[int] = None

class EnergeticoDivisionUpdate(BaseModel):
    NumeroClienteId: Optional[int] = None
    Active: Optional[bool] = None

# --- Modelo para "activos por edificio" (según EnergeticoActivoModel .NET) ---
class UnidadMedidaLite(BaseModel):
    Id: int
    Nombre: Optional[str] = None

class EnergeticoActivoDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    TieneNumCliente: bool
    UnidadesMedida: List[UnidadMedidaLite] = Field(default_factory=list)
