# app/schemas/division.py
from pydantic import BaseModel
from typing import Optional

class DivisionSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config: from_attributes = True

class DivisionListDTO(DivisionSelectDTO):
    Active: Optional[bool] = True
    ServicioId: Optional[int] = None
    RegionId: Optional[int] = None
    ComunaId: Optional[int] = None

class DivisionDTO(DivisionListDTO):
    CreatedAt: Optional[str] = None
    UpdatedAt: Optional[str] = None
    Version: Optional[int] = None
    EdificioId: Optional[int] = None
    ReportaPMG: Optional[bool] = None
    AnyoConstruccion: Optional[int] = None
    Superficie: Optional[float] = None
    TieneMedidorElectricidad: Optional[bool] = None
    TieneMedidorGas: Optional[bool] = None
    ComparteMedidorAgua: Optional[bool] = None
    # (Agregamos más campos si los necesitas en la UI)
