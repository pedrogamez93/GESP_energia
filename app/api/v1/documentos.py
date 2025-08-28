from __future__ import annotations
from typing import Annotated, List
import os
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Path, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.documentos import (
    DocumentoResponse,
    DocumentoBaseIn, ActaDTO, ReunionDTO, ListaIntegrantesDTO, PoliticaDTO, DifusionDTO,
    ProcedimientoPapelDTO, ProcReutilizacionPapelDTO, ProcedimientoResiduoDTO,
    ProcedimientoResiduoSistemaDTO, ProcedimientoBajaBienesDTO, ProcedimientoCompraSustentableDTO,
    CharlasDTO, ListadoColaboradorDTO, CapacitadosMPDTO, GestionCompraSustentableDTO,
    PacE3DTO, ResolucionApruebaPlanDTO, InformeDADTO,
)
from app.db.models.servicio import Servicio
from app.services.documento_service import DocumentoService, CONSTANTS, save_file_from_base64, UPLOAD_DIR
from app.db.models.documento import Documento

from fastapi.responses import FileResponse
from app.core.config import settings
import os



router = APIRouter(prefix="/api/v1/documentos", tags=["Documentos"])
DbDep = Annotated[Session, Depends(get_db)]

def _current_user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None) or request.headers.get("X-User-Id")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="userId no presente")
    return uid

def _paginate_headers(response: Response, total: int, page: int, page_size: int):
    total_pages = (total + page_size - 1) // page_size if page_size else 1
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Total-Pages"] = str(total_pages)

def _inject_servicio_flags(db: Session, resp: DocumentoResponse, servicio_id: int) -> DocumentoResponse:
    srv = db.query(Servicio).filter(Servicio.Id == servicio_id).first()
    if not srv:
        return resp
    resp.NoRegistraPoliticaAmbiental = srv.NoRegistraPoliticaAmbiental
    resp.NoRegistraDifusionInterna   = srv.NoRegistraDifusionInterna
    resp.NoRegistraActividadInterna  = srv.NoRegistraActividadInterna
    resp.NoRegistraReutilizacionPapel = srv.NoRegistraReutilizacionPapel
    resp.NoRegistraProcFormalPapel    = srv.NoRegistraProcFormalPapel
    resp.NoRegistraDocResiduosCertificados = srv.NoRegistraDocResiduosCertificados
    resp.NoRegistraDocResiduosSistemas     = srv.NoRegistraDocResiduosSistemas
    resp.NoRegistraProcBajaBienesMuebles   = srv.NoRegistraProcBajaBienesMuebles
    resp.NoRegistraProcComprasSustentables = srv.NoRegistraProcComprasSustentables
    return resp

# ------------------ DESCARGA de archivos ------------------
@router.get("/file/{filename}", response_class=FileResponse, summary="Descarga de adjunto")
def download_file(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, filename=filename)

@router.get("/file/{filename}", summary="Descarga un archivo adjunto por nombre")
def download_file(filename: str):
    # Evita path traversal
    safe_name = os.path.basename(filename)
    base_dir = settings.FILES_DIR or "/tmp/gesp_documentos"
    full = os.path.join(base_dir, safe_name)
    if not os.path.isfile(full):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado")
    return FileResponse(full, filename=safe_name)

# ------------------ LISTADOS (varios tipos) ------------------

@router.get("/comite", response_model=DocumentoResponse, summary="Actas de Comité (paginado)")
def get_actas_comite(
    response: Response,
    db: DbDep,
    ServicioId: int = Query(..., ge=1),
    Etapa: int | None = Query(default=None),
    AnioDoc: int = Query(default=0, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = DocumentoService(db).q_by_servicio_tipo(ServicioId, CONSTANTS["TIPO_DOCUMENTO_ACTA"], Etapa)
    if AnioDoc > 0:
        q = q.filter(func.extract("year", Documento.CreatedAt) == AnioDoc)
    total = q.count()
    items = q.order_by(Documento.CreatedAt.desc()).offset((page-1)*page_size).limit(page_size).all()
    _paginate_headers(response, total, page, page_size)
    resp = DocumentoResponse(Ok=True, Actas=[{"Id": d.Id, "Fecha": d.Fecha, "AdjuntoNombre": d.AdjuntoNombre} for d in items])
    return _inject_servicio_flags(db, resp, ServicioId)

@router.get("/politica", response_model=DocumentoResponse, summary="Políticas (paginado)")
def get_politicas(
    response: Response,
    db: DbDep,
    ServicioId: int = Query(..., ge=1),
    Etapa: int | None = Query(default=None),
    AnioDoc: int = Query(default=0, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = DocumentoService(db).q_by_servicio_tipo(ServicioId, CONSTANTS["TIPO_DOCUMENTO_POLITICA"], Etapa)
    if AnioDoc > 0:
        q = q.filter(func.extract("year", Documento.CreatedAt) == AnioDoc)
    total = q.count()
    items = q.order_by(Documento.CreatedAt.desc()).offset((page-1)*page_size).limit(page_size).all()
    _paginate_headers(response, total, page, page_size)
    resp = DocumentoResponse(Ok=True, Politicas=[{"Id": d.Id, "Fecha": d.Fecha, "AdjuntoNombre": d.AdjuntoNombre} for d in items])
    return _inject_servicio_flags(db, resp, ServicioId)

@router.get("/difusiones", response_model=DocumentoResponse, summary="Difusiones (paginado)")
def get_difusiones(
    response: Response,
    db: DbDep,
    ServicioId: int = Query(..., ge=1),
    Etapa: int | None = Query(default=None),
    AnioDoc: int = Query(default=0, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = DocumentoService(db).q_by_servicio_tipo(ServicioId, CONSTANTS["TIPO_DOCUMENTO_DIFUSION"], Etapa)
    if AnioDoc > 0:
        q = q.filter(func.extract("year", Documento.CreatedAt) == AnioDoc)
    total = q.count()
    items = q.order_by(Documento.CreatedAt.desc()).offset((page-1)*page_size).limit(page_size).all()
    _paginate_headers(response, total, page, page_size)
    resp = DocumentoResponse(Ok=True, Difusiones=[{"Id": d.Id, "Fecha": d.Fecha, "Cobertura": d.Cobertura} for d in items])
    return _inject_servicio_flags(db, resp, ServicioId)

@router.get("/procedimientos", response_model=DocumentoResponse, summary="Procedimientos (todos, paginado)")
def get_procedimientos(
    response: Response,
    db: DbDep,
    ServicioId: int = Query(..., ge=1),
    AnioDoc: int = Query(default=0, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    tipos = [
        CONSTANTS["TIPO_DOCUMENTO_PROCEDIMIENTO_PAPEL"],
        CONSTANTS["TIPO_DOCUMENTO_PROCEDIMIENTO_RESIDUO"],
        CONSTANTS["TIPO_DOCUMENTO_PROCEDIMIENTO_RESIDUO_SISTEMA"],
        CONSTANTS["TIPO_DOCUMENTO_PROCEDIMIENTO_BAJA_BIENES"],
        CONSTANTS["TIPO_DOCUMENTO_PROCEDIMIENTO_COMPRA_SUSTENTABLE"],
        CONSTANTS["TIPO_DOCUMENTO_PROC_REUTILIZACION_PAPEL"],
    ]
    q = db.query(Documento).filter(Documento.Active == True, Documento.ServicioId == ServicioId, Documento.TipoDocumentoId.in_(tipos))
    if AnioDoc > 0:
        q = q.filter(func.extract("year", Documento.CreatedAt) == AnioDoc)
    total = q.count()
    items = q.order_by(Documento.CreatedAt.desc()).offset((page-1)*page_size).limit(page_size).all()
    _paginate_headers(response, total, page, page_size)
    resp = DocumentoResponse(
        Ok=True,
        Procedimientos=[{"Id": d.Id, "Tipo": d.TipoDocumentoId, "Fecha": d.Fecha, "AdjuntoNombre": d.AdjuntoNombre} for d in items]
    )
    return _inject_servicio_flags(db, resp, ServicioId)

@router.get("/charlas", response_model=DocumentoResponse, summary="Charlas (paginado)")
def get_charlas(
    response: Response,
    db: DbDep,
    ServicioId: int = Query(..., ge=1),
    Etapa: int | None = Query(default=None),
    AnioDoc: int = Query(default=0, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = DocumentoService(db).q_by_servicio_tipo(ServicioId, CONSTANTS["TIPO_DOCUMENTO_CHARLA"], Etapa)
    if AnioDoc > 0:
        q = q.filter(func.extract("year", Documento.CreatedAt) == AnioDoc)
    total = q.count()
    items = q.order_by(Documento.CreatedAt.desc()).offset((page-1)*page_size).limit(page_size).all()
    _paginate_headers(response, total, page, page_size)
    resp = DocumentoResponse(Ok=True, Charlas=[{"Id": d.Id, "NParticipantes": getattr(d, "NParticipantes", 0)} for d in items])
    return _inject_servicio_flags(db, resp, ServicioId)

@router.get("/listado-colaboradores", response_model=DocumentoResponse, summary="Listado colaboradores (paginado)")
def get_listado_colaboradores(
    response: Response,
    db: DbDep,
    ServicioId: int = Query(..., ge=1),
    AnioDoc: int = Query(default=0, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = DocumentoService(db).q_by_servicio_tipo(ServicioId, CONSTANTS["TIPO_DOCUMENTO_LISTADO_COLABORADORES"])
    if AnioDoc > 0:
        q = q.filter(func.extract("year", Documento.CreatedAt) == AnioDoc)
    total = q.count()
    items = q.order_by(Documento.CreatedAt.desc()).offset((page-1)*page_size).limit(page_size).all()
    _paginate_headers(response, total, page, page_size)
    resp = DocumentoResponse(
        Ok=True,
        CapacitadosMP=[{"Id": d.Id, "TotalColaboradoresConcientizados": d.TotalColaboradoresConcientizados, "TotalColaboradoresCapacitados": d.TotalColaboradoresCapacitados} for d in items]
    )
    return _inject_servicio_flags(db, resp, ServicioId)

@router.get("/capacitados-mp", response_model=DocumentoResponse, summary="Capacitados MP (paginado)")
def get_capacitados_mp(
    response: Response, db: DbDep,
    ServicioId: int = Query(..., ge=1),
    AnioDoc: int = Query(default=0, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = DocumentoService(db).q_by_servicio_tipo(ServicioId, CONSTANTS["TIPO_DOCUMENTO_CAPACITADOS_MP"])
    if AnioDoc > 0:
        q = q.filter(func.extract("year", Documento.CreatedAt) == AnioDoc)
    total = q.count()
    items = q.order_by(Documento.CreatedAt.desc()).offset((page-1)*page_size).limit(page_size).all()
    _paginate_headers(response, total, page, page_size)
    resp = DocumentoResponse(Ok=True, CapacitadosMP=[{"Id": d.Id, "TotalColaboradoresCapacitados": d.TotalColaboradoresCapacitados} for d in items])
    return _inject_servicio_flags(db, resp, ServicioId)

@router.get("/gestion-compra-sustentable", response_model=DocumentoResponse, summary="Gestión de compras sustentables (paginado)")
def get_gestion_compra_sustentable(
    response: Response, db: DbDep,
    ServicioId: int = Query(..., ge=1),
    AnioDoc: int = Query(default=0, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = DocumentoService(db).q_by_servicio_tipo(ServicioId, CONSTANTS["TIPO_DOCUMENTO_GESTION_COMPRA_SUSTENTABLE"])
    if AnioDoc > 0:
        q = q.filter(func.extract("year", Documento.CreatedAt) == AnioDoc)
    total = q.count()
    items = q.order_by(Documento.CreatedAt.desc()).offset((page-1)*page_size).limit(page_size).all()
    _paginate_headers(response, total, page, page_size)
    resp = DocumentoResponse(Ok=True, CompraSustentables=[{"Id": d.Id, "NComprasRubros": d.NComprasRubros if hasattr(d, "NComprasRubros") else None} for d in items])
    return _inject_servicio_flags(db, resp, ServicioId)

@router.get("/pac-e3", response_model=DocumentoResponse, summary="PAC E3 (paginado)")
def get_pac_e3(
    response: Response, db: DbDep,
    ServicioId: int = Query(..., ge=1),
    AnioDoc: int = Query(default=0, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = DocumentoService(db).q_by_servicio_tipo(ServicioId, CONSTANTS["TIPO_DOCUMENTO_PAC_E3"])
    if AnioDoc > 0:
        q = q.filter(func.extract("year", Documento.CreatedAt) == AnioDoc)
    total = q.count()
    items = q.order_by(Documento.CreatedAt.desc()).offset((page-1)*page_size).limit(page_size).all()
    _paginate_headers(response, total, page, page_size)
    resp = DocumentoResponse(Ok=True, PacE3s=[{"Id": d.Id, "Fecha": d.Fecha} for d in items])
    return _inject_servicio_flags(db, resp, ServicioId)

@router.get("/informes-da", response_model=DocumentoResponse, summary="Informes DA (paginado)")
def get_informes_da(
    response: Response, db: DbDep,
    ServicioId: int = Query(..., ge=1),
    AnioDoc: int = Query(default=0, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = DocumentoService(db).q_by_servicio_tipo(ServicioId, CONSTANTS["TIPO_DOCUMENTO_INFORME_DA"])
    if AnioDoc > 0:
        q = q.filter(func.extract("year", Documento.CreatedAt) == AnioDoc)
    total = q.count()
    items = q.order_by(Documento.CreatedAt.desc()).offset((page-1)*page_size).limit(page_size).all()
    _paginate_headers(response, total, page, page_size)
    resp = DocumentoResponse(Ok=True, InformeDA=[{"Id": d.Id, "Fecha": d.Fecha} for d in items])
    return _inject_servicio_flags(db, resp, ServicioId)

@router.get("/resoluciones", response_model=DocumentoResponse, summary="Resoluciones aprueba plan (paginado)")
def get_resoluciones(
    response: Response, db: DbDep,
    ServicioId: int = Query(..., ge=1),
    AnioDoc: int = Query(default=0, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = DocumentoService(db).q_by_servicio_tipo(ServicioId, CONSTANTS["TIPO_DOCUMENTO_RESOLUCION_APRUEBA_PLAN"])
    if AnioDoc > 0:
        q = q.filter(func.extract("year", Documento.CreatedAt) == AnioDoc)
    total = q.count()
    items = q.order_by(Documento.CreatedAt.desc()).offset((page-1)*page_size).limit(page_size).all()
    _paginate_headers(response, total, page, page_size)
    resp = DocumentoResponse(Ok=True, ResolucionApruebaPlanDTO=[{"Id": d.Id, "Nresolucion": d.Nresolucion, "Fecha": d.Fecha} for d in items])
    return _inject_servicio_flags(db, resp, ServicioId)

@router.get("/{id}", response_model=DocumentoResponse, summary="Detalle documento por Id")
def get_documento_by_id(id: Annotated[int, Path(ge=1)], db: DbDep):
    obj = DocumentoService(db)._get(id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id, "TipoDocumentoId": obj.TipoDocumentoId, "AdjuntoNombre": obj.AdjuntoNombre})

# ------------------ POST (crear por tipo) ------------------

@router.post("/comite/acta", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_acta(data: ActaDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_acta(data, current_user.id)
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/reunion", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_reunion(data: ReunionDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_reunion(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/lista-integrantes", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_lista_integrantes(data: ListaIntegrantesDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_lista_integrantes(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/politica", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_politica(data: PoliticaDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    adj_rp = save_file_from_base64(data.AdjuntoRespaldo, data.AdjuntoRespaldoPath) if data.AdjuntoRespaldo else None
    adj_part = save_file_from_base64(data.AdjuntoRespaldoParticipativo, data.AdjuntoRespaldoParticipativoPath) if data.AdjuntoRespaldoParticipativo else None
    obj = DocumentoService(db).crear_politica(data, current_user.id, adj_rp, adj_part)
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/difusion", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_difusion(data: DifusionDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_difusion(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/procedimientos/papel", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_proc_papel(data: ProcedimientoPapelDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_proc_papel(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/procedimientos/residuo", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_proc_residuo(data: ProcedimientoResiduoDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_proc_residuo(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/procedimientos/residuo-sistema", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_proc_residuo_sistema(data: ProcedimientoResiduoSistemaDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_proc_residuo_sistema(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/procedimientos/baja-bienes", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_proc_baja_bienes(data: ProcedimientoBajaBienesDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_proc_baja_bienes(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/procedimientos/compra-sustentable", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_proc_compra_sustentable(data: ProcedimientoCompraSustentableDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_proc_compra_sustentable(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/procedimientos/reutilizacion-papel", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_proc_reutilizacion_papel(data: ProcReutilizacionPapelDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_proc_reutilizacion_papel(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/charlas", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_charlas(data: CharlasDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_charla(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/listado-colaborador", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_listado_colaborador(data: ListadoColaboradorDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_listado_colaborador(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/capacitados-mp", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_capacitados_mp(data: CapacitadosMPDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_capacitados_mp(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/gestion-compra-sustentable", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_gestion_compra_sustentable(data: GestionCompraSustentableDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_gestion_compra_sustentable(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/pac-e3", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_pac_e3(data: PacE3DTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_pac_e3(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/informe-da", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_informe_da(data: InformeDADTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_informe_da(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.post("/resolucion-aprueba-plan", response_model=DocumentoResponse, status_code=status.HTTP_201_CREATED)
def post_resolucion_aprueba_plan(data: ResolucionApruebaPlanDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).crear_resolucion_aprueba_plan(data, current_user.id); return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

# ------------------ PUT (actualizar por tipo) ------------------

@router.put("/comite/acta/{id}", response_model=DocumentoResponse)
def put_acta(id: Annotated[int, Path(ge=1)], data: ActaDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_acta(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/reunion/{id}", response_model=DocumentoResponse)
def put_reunion(id: Annotated[int, Path(ge=1)], data: ReunionDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_reunion(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/lista-integrantes/{id}", response_model=DocumentoResponse)
def put_lista_integrantes(id: Annotated[int, Path(ge=1)], data: ListaIntegrantesDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_lista_integrantes(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/politica/{id}", response_model=DocumentoResponse)
def put_politica(id: Annotated[int, Path(ge=1)], data: PoliticaDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    adj_rp = save_file_from_base64(data.AdjuntoRespaldo, data.AdjuntoRespaldoPath) if data.AdjuntoRespaldo else None
    adj_part = save_file_from_base64(data.AdjuntoRespaldoParticipativo, data.AdjuntoRespaldoParticipativoPath) if data.AdjuntoRespaldoParticipativo else None
    obj = DocumentoService(db).actualizar_politica(id, data, current_user.id, adj_rp, adj_part)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/difusion/{id}", response_model=DocumentoResponse)
def put_difusion(id: Annotated[int, Path(ge=1)], data: DifusionDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_difusion(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/procedimientos/papel/{id}", response_model=DocumentoResponse)
def put_proc_papel(id: Annotated[int, Path(ge=1)], data: ProcedimientoPapelDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_proc_papel(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/procedimientos/residuo/{id}", response_model=DocumentoResponse)
def put_proc_residuo(id: Annotated[int, Path(ge=1)], data: ProcedimientoResiduoDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_proc_residuo(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/procedimientos/residuo-sistema/{id}", response_model=DocumentoResponse)
def put_proc_residuo_sistema(id: Annotated[int, Path(ge=1)], data: ProcedimientoResiduoSistemaDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_proc_residuo_sistema(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/procedimientos/baja-bienes/{id}", response_model=DocumentoResponse)
def put_proc_baja_bienes(id: Annotated[int, Path(ge=1)], data: ProcedimientoBajaBienesDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_proc_baja_bienes(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/procedimientos/compra-sustentable/{id}", response_model=DocumentoResponse)
def put_proc_compra_sustentable(id: Annotated[int, Path(ge=1)], data: ProcedimientoCompraSustentableDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_proc_compra_sustentable(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/procedimientos/reutilizacion-papel/{id}", response_model=DocumentoResponse)
def put_proc_reutilizacion_papel(id: Annotated[int, Path(ge=1)], data: ProcReutilizacionPapelDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_proc_reutilizacion_papel(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/charlas/{id}", response_model=DocumentoResponse)
def put_charlas(id: Annotated[int, Path(ge=1)], data: CharlasDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_charla(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/listado-colaborador/{id}", response_model=DocumentoResponse)
def put_listado_colaborador(id: Annotated[int, Path(ge=1)], data: ListadoColaboradorDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_listado_colaborador(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/capacitados-mp/{id}", response_model=DocumentoResponse)
def put_capacitados_mp(id: Annotated[int, Path(ge=1)], data: CapacitadosMPDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_capacitados_mp(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/gestion-compra-sustentable/{id}", response_model=DocumentoResponse)
def put_gestion_compra_sustentable(id: Annotated[int, Path(ge=1)], data: GestionCompraSustentableDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_gestion_compra_sustentable(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/pac-e3/{id}", response_model=DocumentoResponse)
def put_pac_e3(id: Annotated[int, Path(ge=1)], data: PacE3DTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_pac_e3(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/informe-da/{id}", response_model=DocumentoResponse)
def put_informe_da(id: Annotated[int, Path(ge=1)], data: InformeDADTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_informe_da(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

@router.put("/resolucion-aprueba-plan/{id}", response_model=DocumentoResponse)
def put_resolucion_aprueba_plan(id: Annotated[int, Path(ge=1)], data: ResolucionApruebaPlanDTO, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = DocumentoService(db).actualizar_resolucion_aprueba_plan(id, data, current_user.id)
    if not obj: raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True, Documento={"Id": obj.Id})

# ------------------ DELETE ------------------
@router.delete("/{id}", response_model=DocumentoResponse)
def delete_documento(id: Annotated[int, Path(ge=1)], db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    ok = DocumentoService(db).delete(id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentoResponse(Ok=True)
