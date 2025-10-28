# app/services/tipo_luminaria_service.py
from __future__ import annotations

from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

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


def _maybe_set(model_obj, **kwargs):
    """
    Asigna atributos solo si existen en el modelo,
    evitando TypeError por columnas no mapeadas.
    """
    cls = type(model_obj)
    for k, v in kwargs.items():
        if hasattr(cls, k):
            setattr(model_obj, k, v)


class TipoLuminariaService:
    def list(self, db: Session, q: Optional[str], page: int, page_size: int):
        M = _get_model()
        query = db.query(M)
        if q:
            # En SQL Server, collation suele ser case-insensitive;
            # si tu mapeo no soporta ilike, usa .filter(M.Nombre.like(...))
            try:
                query = query.filter(M.Nombre.ilike(f"%{q.strip()}%"))
            except Exception:
                query = query.filter(M.Nombre.like(f"%{q.strip()}%"))

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
        M = _get_model()
        nombre = (payload.Nombre or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre es requerido")

        obj = M(Nombre=nombre)
        # Asigna solo si existen esas columnas en tu modelo/tabla
        _maybe_set(obj, Active=True, CreatedBy=user, ModifiedBy=user)

        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, id: int, payload: CatalogoUpdate, user: Optional[str] = None):
        obj = self.get(db, id)

        if payload.Nombre is not None:
            obj.Nombre = (payload.Nombre or "").strip()

        _maybe_set(obj, ModifiedBy=user)

        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id: int):
        obj = self.get(db, id)
        db.delete(obj)
        db.commit()
