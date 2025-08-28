from pydantic import BaseModel, ConfigDict
from typing import Optional

# ---------- EXISTENTES ----------
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

# ---------- NUEVOS: equivalentes a DTOs .NET ----------
class ObservacionDTO(BaseModel):
    CheckObserva: bool
    Observacion: Optional[str] = None

class ReportaResiduosDTO(BaseModel):
    CheckReporta: bool
    Justificacion: Optional[str] = None
    CheckReportaNoReciclados: bool = False
    JustificacionNoReciclados: Optional[str] = None

class ObservacionInexistenciaDTO(BaseModel):
    Observacion: str

class DivisionPatchDTO(BaseModel):
    NroRol: Optional[str] = None
    SinRol: bool = False
    JustificaRol: Optional[str] = None
    Funcionarios: int = 0
    NroOtrosColaboradores: int = 0
    DisponeVehiculo: Optional[bool] = None
    VehiculosIds: Optional[str] = None
    AccesoFacturaAgua: Optional[int] = None
    InstitucionResponsableAguaId: Optional[int] = None
    ServicioResponsableAguaId: Optional[int] = None
    OrganizacionResponsableAgua: Optional[str] = None
    ComparteMedidorAgua: Optional[bool] = None
    DisponeCalefaccion: bool = False
    AireAcondicionadoElectricidad: bool = False
    CalefaccionGas: bool = False
    GestionBienes: Optional[bool] = None
    UsaBidon: bool = False

class DivisionAniosDTO(BaseModel):
    Id: int
    AnioInicioGestionEnergetica: Optional[int] = None
    AnioInicioRestoItems: Optional[int] = None

# respuestas chicas
class OkMessage(BaseModel):
    Ok: bool = True
    Message: str = "ok"
    model_config = ConfigDict(from_attributes=True)
