from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

# ------- Lecturas / respuestas -------

class ServicioDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    Justificacion: Optional[str] = None
    RevisionRed: bool
    ComentarioRed: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ServicioListDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ServicioResponse(BaseModel):
    Ok: bool
    Servicios: List[ServicioDTO]

class DiagnosticoDTO(BaseModel):
    RevisionDiagnosticoAmbiental: bool
    EtapaSEV: int

# ------- Escrituras parciales (módulo original) -------

class ServicioPatchDTO(BaseModel):
    # banderas ambientales
    NoRegistraPoliticaAmbiental: Optional[bool] = None
    NoRegistraDifusionInterna: Optional[bool] = None
    NoRegistraActividadInterna: Optional[bool] = None
    NoRegistraReutilizacionPapel: Optional[bool] = None
    NoRegistraProcFormalPapel: Optional[bool] = None
    NoRegistraDocResiduosCertificados: Optional[bool] = None
    NoRegistraDocResiduosSistemas: Optional[bool] = None
    NoRegistraProcBajaBienesMuebles: Optional[bool] = None
    NoRegistraProcComprasSustentables: Optional[bool] = None

    # diagnóstico / alcance / compra
    RevisionDiagnosticoAmbiental: Optional[bool] = None
    ColaboradoresModAlcance: Optional[int] = None
    CompraActiva: Optional[bool] = None
    ModificacioAlcance: Optional[bool] = None

    # metacampos (aceptados pero recalculados server-side)
    UpdatedAt: Optional[datetime] = None
    ModifiedBy: Optional[str] = None
    Version: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

# ------- NUEVO: creación / actualización ADMIN -------

class ServicioCreate(BaseModel):
    Nombre: Optional[str] = None
    Identificador: Optional[str] = None
    ReportaPMG: bool
    InstitucionId: int

class ServicioUpdate(BaseModel):
    Nombre: Optional[str] = None
    Identificador: Optional[str] = None
    ReportaPMG: Optional[bool] = None
    InstitucionId: Optional[int] = None
    # campos presentes en Admin Edit
    PgaRevisionRed: Optional[bool] = None
    RevisionRed: Optional[bool] = None
    ValidacionConcientizacion: Optional[bool] = None

# ------- NUEVO: set de estado (activar/desactivar) -------

class ServicioEstadoDTO(BaseModel):
    Active: bool
