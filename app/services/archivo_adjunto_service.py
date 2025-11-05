# app/services/archivo_adjunto_service.py
from __future__ import annotations
import os
from datetime import datetime
from typing import List, Tuple

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.db.models.archivo_adjunto import ArchivoAdjunto
from app.db.models.tipo_archivo import TipoArchivo
from app.db.models.compra import Compra  # <- para setear FacturaId

# Env
FACTURAS_DIR = os.getenv("FACTURAS_DIR", "/var/app/data/facturas")
SMB_UNC_PREFIX = os.getenv("SMB_UNC_PREFIX", "")
SMB_MOUNT_PREFIX = os.getenv("SMB_MOUNT_PREFIX", "")
MAX_SIZE = 4 * 1024 * 1024  # 4MB

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _map_unc_to_local(path: str) -> str:
    if SMB_UNC_PREFIX and SMB_MOUNT_PREFIX and path.startswith(SMB_UNC_PREFIX):
        return path.replace(SMB_UNC_PREFIX, SMB_MOUNT_PREFIX, 1)
    return path

def _read_and_check_size(file: UploadFile) -> bytes:
    data = file.file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="El archivo supera los 4 MB.")
    return data

def _tipo_por_extension_factura(db: Session, ext: str) -> TipoArchivo | None:
    ext = ext.lower()
    return (
        db.query(TipoArchivo)
          .filter(TipoArchivo.FormatoFactura == True)
          .filter(TipoArchivo.Extension.ilike(ext))
          .first()
    )

def get_ext_permitidas_factura(db: Session) -> List[TipoArchivo]:
    return db.query(TipoArchivo).filter(TipoArchivo.FormatoFactura == True).all()

class ArchivoAdjuntoService:
    def add_for_compra(self, db: Session, division_id: int, compra_id: int | None, up: UploadFile) -> int:
        nombre = up.filename or "factura"
        _, ext = os.path.splitext(nombre)
        ext = ext.lower()

        tipo = _tipo_por_extension_factura(db, ext)
        if not tipo:
            raise HTTPException(status_code=400, detail=f"Extensión no permitida para factura: {ext}")

        _ensure_dir(FACTURAS_DIR)
        destino = os.path.join(FACTURAS_DIR, f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext}")
        data = _read_and_check_size(up)
        with open(destino, "wb") as f:
            f.write(data)

        adj = ArchivoAdjunto(
            CreatedAt=datetime.now(),
            UpdatedAt=None,
            Version=1,
            Active=True,
            ModifiedBy=None,
            CreatedBy=None,
            Nombre=nombre,
            Descripcion=None,
            DivisionId=division_id,
            TipoArchivoId=tipo.Id,
            Url=destino,
        )
        db.add(adj)
        db.flush()  # adj.Id

        # 🔗 Si nos pasaron compra_id, enlazamos la factura a la compra
        if compra_id:
            comp = db.get(Compra, compra_id)
            if not comp:
                raise HTTPException(status_code=404, detail="Compra no encontrada para asociar factura.")
            comp.FacturaId = adj.Id
            comp.UpdatedAt = datetime.utcnow()
            comp.Version = (comp.Version or 0) + 1
            db.add(comp)

        return adj.Id

    def replace(self, db: Session, archivo_id: int, division_id: int, up: UploadFile) -> None:
        adj = db.get(ArchivoAdjunto, archivo_id)
        if not adj:
            raise HTTPException(status_code=404, detail="Archivo no existe.")

        nombre = up.filename or adj.Nombre
        _, ext = os.path.splitext(nombre)
        ext = ext.lower()

        tipo = _tipo_por_extension_factura(db, ext)
        if not tipo:
            raise HTTPException(status_code=400, detail=f"Extensión no permitida para factura: {ext}")

        _ensure_dir(FACTURAS_DIR)
        destino = os.path.join(FACTURAS_DIR, f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext}")
        data = _read_and_check_size(up)
        with open(destino, "wb") as f:
            f.write(data)

        # (opcional) borrar archivo anterior físico
        # try:
        #     prev = _map_unc_to_local(adj.Url)
        #     if prev and os.path.exists(prev):
        #         os.remove(prev)
        # except Exception:
        #     pass

        adj.Nombre = nombre
        adj.Url = destino
        adj.DivisionId = division_id
        adj.TipoArchivoId = tipo.Id
        adj.UpdatedAt = datetime.now()
        adj.Version = (adj.Version or 0) + 1
        db.add(adj)

    def get_by_factura_id(self, db: Session, factura_id: int) -> Tuple[bytes, str, str]:
        adj = db.query(ArchivoAdjunto).filter(ArchivoAdjunto.Id == factura_id).first()
        if not adj:
            raise HTTPException(status_code=404, detail="Archivo no existe.")

        path = _map_unc_to_local(adj.Url)
        if not os.path.exists(path):
            raise HTTPException(status_code=400, detail="Archivo no existe en disco.")

        tipo = db.get(TipoArchivo, adj.TipoArchivoId)
        mime = tipo.MimeType if tipo and tipo.MimeType else "application/octet-stream"

        with open(path, "rb") as f:
            return f.read(), mime, adj.Nombre
