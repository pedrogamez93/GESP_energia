# app/services/tipo_luminaria_service.py
from __future__ import annotations

from typing import Optional
import re

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.schemas.catalogo_simple import CatalogoCreate, CatalogoUpdate


def _get_model():
    """
    Importa el modelo TipoLuminaria probando rutas comunes.
    Lanza un error claro si no lo encuentra.
    """
    try:
        # Ruta 1: app/models/tipo_luminaria.py -> class TipoLuminaria
        from app.models.tipo_luminaria import TipoLuminaria as M
        return M
    except ModuleNotFoundError:
        try:
            # Ruta 2: app/db/models/tipo_luminaria.py -> class TipoLuminaria
            from app.db.models.tipo_luminaria import TipoLuminaria as M
            return M
        except ModuleNotFoundError as e:
            raise ImportError(
                "No se encontró el modelo 'TipoLuminaria'. "
                "Revisa que exista 'app/models/tipo_luminaria.py' o 'app/db/models/tipo_luminaria.py' "
                "y que declare la clase 'TipoLuminaria'."
            ) from e


def _model_has(model_or_cls, attr: str) -> bool:
    """True si el atributo existe en el modelo SQLAlchemy."""
    cls = model_or_cls if isinstance(model_or_cls, type) else type(model_or_cls)
    return hasattr(cls, attr)


def _safe_defaults(M) -> dict:
    """
    Devuelve un dict con defaults (=0) SOLO para columnas que existan
    en el modelo. Esto evita violaciones NOT NULL en la tabla
    TiposLuminarias, sin depender de defaults en la BD.
    """
    candidate_zero_fields = [
        # Cantidades (Q_*):
        "Q_Educacion", "Q_Oficinas", "Q_Salud", "Q_Seguridad",
        # Áreas:
        "Area_Educacion", "Area_Oficinas", "Area_Salud", "Area_Seguridad",
        # Vida útil y costos:
        "Vida_Util", "Costo_Lamp", "Costo_Lum",
        "Costo_Social_Lamp", "Costo_Social_Lum",
        # Mano de obra (ejecución / reposición):
        "Ejec_HD_Maestro", "Ejec_HD_Ayte", "Ejec_HD_Jornal",
        "Rep_HD_Maestro", "Rep_HD_Ayte", "Rep_HD_Jornal",
    ]
    out = {}
    for f in candidate_zero_fields:
        if _model_has(M, f):
            out[f] = 0
    # Banderas / metadatos comunes si existen
    if _model_has(M, "Active"):
        out["Active"] = True
    return out


def _raise_integrity(e: IntegrityError, friendly: str):
    """Levanta HTTP 400 con mejor detalle (intenta detectar la columna)."""
    msg = str(getattr(e, "orig", e))
    m = re.search(r"column '([^']+)'", msg, re.I) or re.search(r"Column '([^']+)'", msg, re.I)
    col = m.group(1) if m else None
    detail = {
        "code": "integrity_error",
        "message": friendly,
        "column": col,
        "db_message": msg[:600],
    }
    raise HTTPException(status_code=400, detail=detail)


class TipoLuminariaService:
    def list(self, db: Session, q: Optional[str], page: int, page_size: int):
        M = _get_model()
        query = db.query(M)
        if q:
            qs = q.strip()
            try:
                query = query.filter(M.Nombre.ilike(f"%{qs}%"))
            except Exception:
                query = query.filter(M.Nombre.like(f"%{qs}%"))

        total = query.count()
        items = (
            query.order_by(M.Id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def get(self, db: Session, id: int):
        M = _get_model()
        obj = db.get(M, id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
        return obj

    def create(self, db: Session, payload: CatalogoCreate, user: Optional[str] = None):
        """
        Crea una luminaria. Como la tabla tiene varias columnas NOT NULL,
        completamos con 0 por defecto para evitar violaciones de integridad
        cuando el front solo envía 'Nombre' (y eventualmente Vida_Util / Costos).
        """
        M = _get_model()
        nombre = (payload.Nombre or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre es requerido")

        values = _safe_defaults(M)
        values["Nombre"] = nombre

        # Si por accidente tu DTO ya trae Vida_Util / Costo_* intenta usarlos (si existen):
        # NOTA: CatalogoCreate no los define, pero esto no rompe si no están.
        for k in ("Vida_Util", "Costo_Lamp", "Costo_Lum"):
            if _model_has(M, k) and hasattr(payload, k) and getattr(payload, k) is not None:
                values[k] = getattr(payload, k)

        # Metadatos de auditoría si existen en el modelo
        if _model_has(M, "CreatedBy"):
            values["CreatedBy"] = user
        if _model_has(M, "ModifiedBy"):
            values["ModifiedBy"] = user

        obj = M(**values)
        db.add(obj)
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            _raise_integrity(e, "No se pudo crear la luminaria por columnas requeridas.")
        db.refresh(obj)
        return obj

    def update(self, db: Session, id: int, payload: CatalogoUpdate, user: Optional[str] = None):
        M = _get_model()
        obj = self.get(db, id)

        if payload.Nombre is not None:
            obj.Nombre = (payload.Nombre or "").strip()

        # Metadatos de auditoría
        if _model_has(M, "ModifiedBy"):
            obj.ModifiedBy = user

        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            _raise_integrity(e, "No se pudo actualizar la luminaria.")
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id: int):
        obj = self.get(db, id)
        db.delete(obj)
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            _raise_integrity(e, "No se pudo eliminar la luminaria.")
