# app/services/archivo_adjunto_service.py
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.db.models.archivo_adjunto import ArchivoAdjunto
from app.db.models.tipo_archivo import TipoArchivo
from app.db.models.compra import Compra  # para setear FacturaId

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
FACTURAS_DIR = os.getenv("FACTURAS_DIR", "/var/app/data/facturas")
SMB_UNC_PREFIX = os.getenv("SMB_UNC_PREFIX", "")
SMB_MOUNT_PREFIX = os.getenv("SMB_MOUNT_PREFIX", "")
MAX_SIZE = 4 * 1024 * 1024  # 4 MB

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)

def _map_unc_to_local(path: str) -> str:
    if SMB_UNC_PREFIX and SMB_MOUNT_PREFIX and path.startswith(SMB_UNC_PREFIX):
        return path.replace(SMB_UNC_PREFIX, SMB_MOUNT_PREFIX, 1)
    return path

def _read_and_check_size(file: UploadFile) -> bytes:
    # Nota: UploadFile.file es un SpooledTemporaryFile
    file.file.seek(0)
    data = file.file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="El archivo supera los 4 MB.")
    return data

_slug_re = re.compile(r"[^a-zA-Z0-9._-]+")

def _slugify_filename(name: str) -> str:
    # quita rutas y deja un nombre “seguro”
    base = os.path.basename(name or "factura")
    base = base.strip().replace(" ", "_")
    base = _slug_re.sub("", base)
    return base or "factura"

def _tipo_por_extension_factura(db: Session, ext: str) -> TipoArchivo | None:
    """Busca TipoArchivo para facturas por extensión, tolerando con/sin punto."""
    ext = (ext or "").lower()
    ext_dot = ext if ext.startswith(".") else f".{ext}" if ext else ext
    ext_nodot = ext_dot[1:] if ext_dot.startswith(".") else ext_dot
    # intenta match exacto (ilike) tanto '.pdf' como 'pdf'
    q = (
        db.query(TipoArchivo)
          .filter(TipoArchivo.FormatoFactura == True)
          .filter(
              (TipoArchivo.Extension.ilike(ext_dot)) |
              (TipoArchivo.Extension.ilike(ext_nodot))
          )
          .first()
    )
    return q

def get_ext_permitidas_factura(db: Session) -> List[TipoArchivo]:
    return db.query(TipoArchivo).filter(TipoArchivo.FormatoFactura == True).all()

# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────
class ArchivoAdjuntoService:
    def add_for_compra(self, db: Session, division_id: int, compra_id: int | None, up: UploadFile) -> int:
        # 1) Validaciones básicas y normalización
        original_name = _slugify_filename(up.filename or "factura")
        _, ext = os.path.splitext(original_name)
        ext = ext.lower()

        tipo = _tipo_por_extension_factura(db, ext)
        if not tipo:
            raise HTTPException(status_code=400, detail=f"Extensión no permitida para factura: {ext or '(sin extensión)'}")

        # 2) Guardar archivo físico
        _ensure_dir(FACTURAS_DIR)
        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        final_name = f"{stamp}_{original_name}"
        destino = os.path.join(FACTURAS_DIR, final_name)

        data = _read_and_check_size(up)
        with open(destino, "wb") as f:
            f.write(data)

        # 3) Insert en ArchivoAdjuntos (IMPORTANTE: UpdatedAt NOT NULL)
        now = datetime.now()  # tu esquema usa timezone=False
        adj = ArchivoAdjunto(
            CreatedAt=now,
            UpdatedAt=now,            # ← FIX principal (no NULL)
            Version=1,
            Active=True,
            ModifiedBy=None,
            CreatedBy=None,
            Nombre=original_name,     # guardo nombre “humano”
            Descripcion=None,
            DivisionId=division_id,
            TipoArchivoId=tipo.Id,
            Url=destino,              # ruta absoluta (o UNC si mapeas)
        )
        db.add(adj)
        db.flush()  # para obtener adj.Id

        # 4) Enlazar con Compra (si corresponde)
        if compra_id:
            comp = db.get(Compra, compra_id)
            if not comp:
                raise HTTPException(status_code=404, detail="Compra no encontrada para asociar factura.")
            comp.FacturaId = adj.Id
            comp.UpdatedAt = now
            comp.Version = (comp.Version or 0) + 1
            db.add(comp)

        return adj.Id

    def replace(self, db: Session, archivo_id: int, division_id: int, up: UploadFile) -> None:
        adj = db.get(ArchivoAdjunto, archivo_id)
        if not adj:
            raise HTTPException(status_code=404, detail="Archivo no existe.")

        original_name = _slugify_filename(up.filename or adj.Nombre)
        _, ext = os.path.splitext(original_name)
        ext = ext.lower()

        tipo = _tipo_por_extension_factura(db, ext)
        if not tipo:
            raise HTTPException(status_code=400, detail=f"Extensión no permitida para factura: {ext or '(sin extensión)'}")

        _ensure_dir(FACTURAS_DIR)
        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        final_name = f"{stamp}_{original_name}"
        destino = os.path.join(FACTURAS_DIR, final_name)

        data = _read_and_check_size(up)
        with open(destino, "wb") as f:
            f.write(data)

        # (opcional) borrar archivo anterior físico:
        # try:
        #     prev = _map_unc_to_local(adj.Url or "")
        #     if prev and os.path.exists(prev):
        #         os.remove(prev)
        # except Exception:
        #     pass

        now = datetime.now()
        adj.Nombre = original_name
        adj.Url = destino
        adj.DivisionId = division_id
        adj.TipoArchivoId = tipo.Id
        adj.UpdatedAt = now          # ← asegura NOT NULL
        adj.Version = (adj.Version or 0) + 1
        db.add(adj)

    def get_by_factura_id(self, db: Session, factura_id: int) -> Tuple[bytes, str, str]:
        adj = db.query(ArchivoAdjunto).filter(ArchivoAdjunto.Id == factura_id).first()
        if not adj:
            raise HTTPException(status_code=404, detail="Archivo no existe.")

        path = _map_unc_to_local(adj.Url or "")
        if not path or not os.path.exists(path):
            raise HTTPException(status_code=400, detail="Archivo no existe en disco.")

        tipo = db.get(TipoArchivo, adj.TipoArchivoId) if adj.TipoArchivoId else None
        mime = (tipo.MimeType if tipo and tipo.MimeType else "application/octet-stream")

        with open(path, "rb") as f:
            return f.read(), mime, adj.Nombre or "factura"
