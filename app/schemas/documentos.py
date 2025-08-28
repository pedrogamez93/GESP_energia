from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

# ---------- Respuesta genérica (par con .NET) ----------
class DocumentoResponse(BaseModel):
    Ok: bool = True
    Msj: Optional[str] = None

    # banderas que .NET inyecta desde Servicio
    NoRegistraPoliticaAmbiental: Optional[bool] = None
    NoRegistraDifusionInterna:   Optional[bool] = None
    NoRegistraActividadInterna:  Optional[bool] = None
    NoRegistraReutilizacionPapel: Optional[bool] = None
    NoRegistraProcFormalPapel:    Optional[bool] = None
    NoRegistraDocResiduosCertificados: Optional[bool] = None
    NoRegistraDocResiduosSistemas:     Optional[bool] = None
    NoRegistraProcBajaBienesMuebles:   Optional[bool] = None
    NoRegistraProcComprasSustentables: Optional[bool] = None

    # colecciones por categoría (se llenan según endpoint)
    Actas: Optional[List[dict]] = None
    Reuniones: Optional[List[dict]] = None
    ListasIntegrantes: Optional[List[dict]] = None
    Politicas: Optional[List[dict]] = None
    Difusiones: Optional[List[dict]] = None
    Procedimientos: Optional[List[dict]] = None
    Charlas: Optional[List[dict]] = None
    CapacitadosMP: Optional[List[dict]] = None
    PacE3s: Optional[List[dict]] = None
    CompraSustentables: Optional[List[dict]] = None

    # ítems únicos
    Documento: Optional[dict] = None
    Politica: Optional[dict] = None
    Difusion: Optional[dict] = None
    CompraSustentable: Optional[dict] = None
    PacE3: Optional[dict] = None
    InformeDA: Optional[dict] = None
    ResolucionApruebaPlanDTO: Optional[dict] = None

# ---------- DTOs base de creación/edición ----------
class DocumentoBaseIn(BaseModel):
    ServicioId: int
    Fecha: Optional[datetime] = None
    Observaciones: Optional[str] = None
    EtapaSEV_docs: Optional[int] = None
    Titulo: Optional[str] = None
    Materia: Optional[str] = None

    # archivo principal (par con .NET: base64 y path)
    Adjunto: Optional[str] = None           # base64
    AdjuntoPath: Optional[str] = None       # nombre original

class DocumentoIdOut(BaseModel):
    Id: int
    model_config = ConfigDict(from_attributes=True)

# ---- Ejemplos de DTOs específicos (añade campos según formulario real) ----
class ActaDTO(DocumentoBaseIn): pass
class ReunionDTO(DocumentoBaseIn): pass

class ListaIntegrantesDTO(DocumentoBaseIn):
    NParticipantes: Optional[int] = None
    # TODO: Integrantes: List[IntegranteDTO] si lo usas

class PoliticaDTO(DocumentoBaseIn):
    GestionPapel: Optional[bool] = None
    EficienciaEnergetica: Optional[bool] = None
    ComprasSustentables: Optional[bool] = None
    Otras: Optional[str] = None
    # Respaldos
    AdjuntoRespaldo: Optional[str] = None
    AdjuntoRespaldoPath: Optional[str] = None
    AdjuntoRespaldoParticipativo: Optional[str] = None
    AdjuntoRespaldoParticipativoPath: Optional[str] = None

class DifusionDTO(DocumentoBaseIn):
    Cobertura: Optional[int] = None

class ProcedimientoPapelDTO(DocumentoBaseIn):
    DifusionInterna: Optional[bool] = None
    Implementacion: Optional[bool] = None
    ImpresionDobleCara: Optional[bool] = None
    BajoConsumoTinta: Optional[bool] = None

class ProcReutilizacionPapelDTO(DocumentoBaseIn):
    # si tiene campos extra, agrégalos aquí
    pass

class ProcedimientoResiduoDTO(DocumentoBaseIn): pass
class ProcedimientoResiduoSistemaDTO(DocumentoBaseIn): pass
class ProcedimientoBajaBienesDTO(DocumentoBaseIn): pass
class ProcedimientoCompraSustentableDTO(DocumentoBaseIn): pass

class CharlasDTO(DocumentoBaseIn):
    NParticipantes: Optional[int] = 0
    # Adjunto(s) invitación/fotos (si aplica)
    AdjuntoInvitacion: Optional[str] = None
    AdjuntoInvitacionPath: Optional[str] = None
    AdjuntoFotografias: Optional[str] = None
    AdjuntoFotografiasPath: Optional[str] = None

class ListadoColaboradorDTO(DocumentoBaseIn):
    TotalColaboradoresConcientizados: Optional[float] = None
    TotalColaboradoresCapacitados: Optional[int] = None

class CapacitadosMPDTO(DocumentoBaseIn):
    TotalColaboradoresCapacitados: Optional[int] = None

class GestionCompraSustentableDTO(DocumentoBaseIn):
    NComprasRubros: Optional[int] = None
    NComprasCriterios: Optional[int] = None

class PacE3DTO(DocumentoBaseIn):
    AdjuntoRespaldoCompromiso: Optional[str] = None
    AdjuntoRespaldoCompromisoPath: Optional[str] = None

class ResolucionApruebaPlanDTO(DocumentoBaseIn):
    Nresolucion: Optional[str] = None

class InformeDADTO(DocumentoBaseIn): pass
