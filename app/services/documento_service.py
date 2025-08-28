from __future__ import annotations
from datetime import datetime
from typing import Type
import base64, secrets
from app.core.config import settings
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models.documento import (
    Documento, ActaComite, Reunion, ListaIntegrante, Politica, DifusionPolitica,
    ProcedimientoPapel, ProcedimientoResiduo, ProcedimientoResiduoSistema, ProcedimientoBajaBienes,
    ProcedimientoCompraSustentable, ProcReutilizacionPapel, Charla, ListadoColaborador,
    CapacitadosMP, GestionCompraSustentable, PacE3, InformeDA, ResolucionApruebaPlan
)
from app.schemas.documentos import DocumentoBaseIn

CONSTANTS = {
    "TIPO_DOCUMENTO_ACTA": 1,
    "TIPO_DOCUMENTO_REUNION": 2,
    "TIPO_DOCUMENTO_LISTA_INTEGRANTES": 3,
    "TIPO_DOCUMENTO_POLITICA": 4,
    "TIPO_DOCUMENTO_DIFUSION": 5,
    "TIPO_DOCUMENTO_PROCEDIMIENTO_PAPEL": 6,
    "TIPO_DOCUMENTO_PROCEDIMIENTO_RESIDUO": 1005,
    "TIPO_DOCUMENTO_PROCEDIMIENTO_RESIDUO_SISTEMA": 1006,
    "TIPO_DOCUMENTO_PROCEDIMIENTO_BAJA_BIENES": 1007,
    "TIPO_DOCUMENTO_PROCEDIMIENTO_COMPRA_SUSTENTABLE": 1008,
    "TIPO_DOCUMENTO_CHARLA": 1009,
    "TIPO_DOCUMENTO_LISTADO_COLABORADORES": 1010,
    "TIPO_DOCUMENTO_PROC_REUTILIZACION_PAPEL": 1011,
    "TIPO_DOCUMENTO_CAPACITADOS_MP": 1012,
    "TIPO_DOCUMENTO_GESTION_COMPRA_SUSTENTABLE": 1013,
    "TIPO_DOCUMENTO_PAC_E3": 1015,
    "TIPO_DOCUMENTO_INFORME_DA": 1016,
    "TIPO_DOCUMENTO_RESOLUCION_APRUEBA_PLAN": 1017,
}

UPLOAD_DIR = settings.FILES_DIR or "/tmp/gesp_documentos"

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def save_file_from_base64(b64: str, original_name: str | None) -> tuple[str, str]:
    ensure_dir(UPLOAD_DIR)
    ext = ""
    if original_name and "." in original_name:
        ext = "." + original_name.split(".")[-1]
    token = secrets.token_hex(16)
    gen_name = f"{token}{ext}"
    full = os.path.join(UPLOAD_DIR, gen_name)
    with open(full, "wb") as f:
        f.write(base64.b64decode(b64))
    return gen_name, original_name or gen_name

class DocumentoService:
    def __init__(self, db: Session):
        self.db = db

    # -------- Helpers --------
    def _new_doc(self, cls: Type[Documento], data: DocumentoBaseIn, tipo_id: int, user_id: str) -> Documento:
        now = datetime.utcnow()
        obj = cls(
            CreatedAt=now, UpdatedAt=now, Version=1, Active=True,
            CreatedBy=user_id, ModifiedBy=user_id,
            ServicioId=data.ServicioId,
            Fecha=data.Fecha,
            Observaciones=data.Observaciones,
            EtapaSEV_docs=data.EtapaSEV_docs,
            Titulo=data.Titulo,
            Materia=data.Materia,
            TipoDocumentoId=tipo_id,
        )
        if data.Adjunto:
            nombre, original = save_file_from_base64(data.Adjunto, data.AdjuntoPath)
            obj.AdjuntoUrl = nombre
            obj.AdjuntoNombre = original
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def _update_common(self, obj: Documento, data: DocumentoBaseIn, user_id: str) -> Documento:
        for k, v in data.model_dump(exclude_unset=True).items():
            if k in {"Adjunto", "AdjuntoPath"}:
                continue
            setattr(obj, k, v)
        if data.Adjunto:
            nombre, original = save_file_from_base64(data.Adjunto, data.AdjuntoPath)
            obj.AdjuntoUrl = nombre
            obj.AdjuntoNombre = original
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = user_id
        obj.Version = (obj.Version or 0) + 1
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def _get(self, doc_id: int) -> Documento | None:
        return self.db.query(Documento).filter(Documento.Id == doc_id).first()

    def delete(self, doc_id: int, user_id: str) -> bool:
        obj = self._get(doc_id)
        if not obj:
            return False
        if not obj.Active:
            return True
        obj.Active = False
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = user_id
        obj.Version = (obj.Version or 0) + 1
        self.db.commit()
        return True

    def q_by_servicio_tipo(self, servicio_id: int, tipo_id: int, etapa: int | None = None):
        q = self.db.query(Documento).filter(
            Documento.Active == True,
            Documento.ServicioId == servicio_id,
            Documento.TipoDocumentoId == tipo_id,
        )
        if etapa is not None:
            q = q.filter(Documento.EtapaSEV_docs == etapa)
        return q

    # -------- Crear / Actualizar: TODOS los subtipos --------
    def crear_acta(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(ActaComite, data, CONSTANTS["TIPO_DOCUMENTO_ACTA"], user_id)
    def actualizar_acta(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_reunion(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(Reunion, data, CONSTANTS["TIPO_DOCUMENTO_REUNION"], user_id)
    def actualizar_reunion(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_lista_integrantes(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(ListaIntegrante, data, CONSTANTS["TIPO_DOCUMENTO_LISTA_INTEGRANTES"], user_id)
    def actualizar_lista_integrantes(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_politica(self, data: DocumentoBaseIn, user_id: str,
                       adj_rp: tuple[str,str] | None = None,
                       adj_part: tuple[str,str] | None = None) -> Documento:
        obj = self._new_doc(Politica, data, CONSTANTS["TIPO_DOCUMENTO_POLITICA"], user_id)
        if adj_rp:
            obj.AdjuntoRespaldoUrl, obj.AdjuntoRespaldoNombre = adj_rp
        if adj_part:
            obj.AdjuntoRespaldoUrlParticipativo, obj.AdjuntoRespaldoNombreParticipativo = adj_part
        self.db.commit(); self.db.refresh(obj)
        return obj
    def actualizar_politica(self, doc_id: int, data: DocumentoBaseIn, user_id: str,
                            adj_rp: tuple[str,str] | None = None,
                            adj_part: tuple[str,str] | None = None) -> Documento | None:
        obj = self._get(doc_id)
        if not obj: return None
        obj = self._update_common(obj, data, user_id)
        if adj_rp:
            obj.AdjuntoRespaldoUrl, obj.AdjuntoRespaldoNombre = adj_rp
        if adj_part:
            obj.AdjuntoRespaldoUrlParticipativo, obj.AdjuntoRespaldoNombreParticipativo = adj_part
        self.db.commit(); self.db.refresh(obj)
        return obj

    def crear_difusion(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(DifusionPolitica, data, CONSTANTS["TIPO_DOCUMENTO_DIFUSION"], user_id)
    def actualizar_difusion(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_proc_papel(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(ProcedimientoPapel, data, CONSTANTS["TIPO_DOCUMENTO_PROCEDIMIENTO_PAPEL"], user_id)
    def actualizar_proc_papel(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_proc_residuo(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(ProcedimientoResiduo, data, CONSTANTS["TIPO_DOCUMENTO_PROCEDIMIENTO_RESIDUO"], user_id)
    def actualizar_proc_residuo(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_proc_residuo_sistema(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(ProcedimientoResiduoSistema, data, CONSTANTS["TIPO_DOCUMENTO_PROCEDIMIENTO_RESIDUO_SISTEMA"], user_id)
    def actualizar_proc_residuo_sistema(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_proc_baja_bienes(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(ProcedimientoBajaBienes, data, CONSTANTS["TIPO_DOCUMENTO_PROCEDIMIENTO_BAJA_BIENES"], user_id)
    def actualizar_proc_baja_bienes(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_proc_compra_sustentable(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(ProcedimientoCompraSustentable, data, CONSTANTS["TIPO_DOCUMENTO_PROCEDIMIENTO_COMPRA_SUSTENTABLE"], user_id)
    def actualizar_proc_compra_sustentable(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_proc_reutilizacion_papel(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(ProcReutilizacionPapel, data, CONSTANTS["TIPO_DOCUMENTO_PROC_REUTILIZACION_PAPEL"], user_id)
    def actualizar_proc_reutilizacion_papel(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_charla(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(Charla, data, CONSTANTS["TIPO_DOCUMENTO_CHARLA"], user_id)
    def actualizar_charla(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_listado_colaborador(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(ListadoColaborador, data, CONSTANTS["TIPO_DOCUMENTO_LISTADO_COLABORADORES"], user_id)
    def actualizar_listado_colaborador(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_capacitados_mp(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(CapacitadosMP, data, CONSTANTS["TIPO_DOCUMENTO_CAPACITADOS_MP"], user_id)
    def actualizar_capacitados_mp(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_gestion_compra_sustentable(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(GestionCompraSustentable, data, CONSTANTS["TIPO_DOCUMENTO_GESTION_COMPRA_SUSTENTABLE"], user_id)
    def actualizar_gestion_compra_sustentable(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_pac_e3(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(PacE3, data, CONSTANTS["TIPO_DOCUMENTO_PAC_E3"], user_id)
    def actualizar_pac_e3(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_informe_da(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(InformeDA, data, CONSTANTS["TIPO_DOCUMENTO_INFORME_DA"], user_id)
    def actualizar_informe_da(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None

    def crear_resolucion_aprueba_plan(self, data: DocumentoBaseIn, user_id: str) -> Documento:
        return self._new_doc(ResolucionApruebaPlan, data, CONSTANTS["TIPO_DOCUMENTO_RESOLUCION_APRUEBA_PLAN"], user_id)
    def actualizar_resolucion_aprueba_plan(self, doc_id: int, data: DocumentoBaseIn, user_id: str) -> Documento | None:
        obj = self._get(doc_id)
        return self._update_common(obj, data, user_id) if obj else None
