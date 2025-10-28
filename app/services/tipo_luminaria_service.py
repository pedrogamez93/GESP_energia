# app/services/tipo_luminaria_service.py
from __future__ import annotations

from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.tipo_luminaria import TipoLuminaria
from app.schemas.catalogo_simple import CatalogoCreate, CatalogoUpdate


def _maybe_set(model_obj, **kwargs):
    """
    Asigna atributos solo si existen en el modelo,
    evitando TypeError por columnas que no están mapeadas.
    """
    cls = type(model_obj)
    for k, v in kwargs.items():
        if hasattr(cls, k):
            setattr(model_obj, k, v)


class TipoLuminariaService:
    # Listado paginado con filtro por nombre
    def list(self, db: Session, q: Optional[str], page: int, page_size: int):
        query = db.query(TipoLuminaria)
        if q:
            # ilike si la BD lo permite; en SQL Server se traduce a LIKE case-insensitive por collation
            query = query.filter(TipoLuminaria.Nombre.ilike(f"%{q.strip()}%"))
        total = query.count()
        items = (
            query.order_by(TipoLuminaria.Id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        }

    # Obtener por id
    def get(self, db: Session, id: int):
        obj = db.get(TipoLuminaria, id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
        return obj

    # Crear (solo usa campos válidos; NO pasa CreatedAt/UpdatedAt)
    def create(self, db: Session, payload: CatalogoCreate, user: Optional[str] = None):
        nombre = (payload.Nombre or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre es requerido")

        obj = TipoLuminaria(Nombre=nombre)
        # opcionales si existen en el modelo
        _maybe_set(obj,
                   Active=True,
                   CreatedBy=user,
                   ModifiedBy=user)

        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Actualizar
    def update(self, db: Session, id: int, payload: CatalogoUpdate, user: Optional[str] = None):
        obj = self.get(db, id)
        # setea solo lo que venga en payload
        if payload.Nombre is not None:
            obj.Nombre = payload.Nombre.strip()
        # opcional si la columna existe
        _maybe_set(obj, ModifiedBy=user)

        db.commit()
        db.refresh(obj)
        return obj

    # Eliminar
    def delete(self, db: Session, id: int):
        obj = self.get(db, id)
        db.delete(obj)
        db.commit()
