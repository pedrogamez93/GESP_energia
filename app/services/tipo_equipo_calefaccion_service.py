# app/services/tipo_equipo_calefaccion_service.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.inspection import inspect as sa_inspect

# Ajusta este import a tu estructura real:
# Si tu modelo vive en otra ruta, por ejemplo app.models.catalogos, cámbialo.
from app.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion  # <- AJUSTAR SI ES NECESARIO


def _to_snake(name: str) -> str:
    """
    Convierte claves CamelCase/PascalCase a snake_case.
    Ej: 'CreatedAt' -> 'created_at', 'tipoEquipo' -> 'tipo_equipo'
    """
    if not name:
        return name
    out = []
    prev_lower = False
    prev_char = ""
    for ch in name:
        if ch.isupper() and (prev_lower or (prev_char and prev_char.isalpha())):
            out.append("_")
        out.append(ch.lower())
        prev_lower = ch.islower()
        prev_char = ch
    return "".join(out)


def _as_dict(payload: Any) -> Dict[str, Any]:
    """
    Convierte el payload a dict sin campos no seteados si es BaseModel.
    """
    if hasattr(payload, "model_dump"):  # Pydantic v2
        return payload.model_dump(exclude_unset=True)
    if hasattr(payload, "dict"):  # Pydantic v1
        return payload.dict(exclude_unset=True)
    if isinstance(payload, dict):
        return dict(payload)
    raise TypeError("El payload debe ser un dict o un BaseModel de Pydantic.")


def _model_field_names(model) -> Tuple[set, set]:
    """
    Retorna dos sets: (column_names, relationship_names) del modelo SQLAlchemy.
    Sirve para filtrar kwargs válidos para el constructor.
    """
    mapper = sa_inspect(model)
    cols = {attr.key for attr in mapper.attrs if hasattr(attr, "columns")}
    rels = {rel.key for rel in mapper.relationships}
    return cols, rels


def _filter_to_model_fields(model, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deja solo las claves que el modelo soporta: columnas + relaciones.
    """
    column_names, relationship_names = _model_field_names(model)
    allowed = column_names | relationship_names
    return {k: v for k, v in data.items() if k in allowed}


class TipoEquipoCalefaccionService:
    """
    Servicio para el catálogo de Tipos de Equipos de Calefacción.
    Maneja CRUD, paginación y campos de auditoría si existen en el modelo.
    """

    # --------------------------
    # Lectura / Listado
    # --------------------------
    def list(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        order_by: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Retorna una página del catálogo. Aplica filtros simples.
        """
        q = db.query(TipoEquipoCalefaccion)

        # Filtro por is_active si la columna existe
        cols, _ = _model_field_names(TipoEquipoCalefaccion)
        if is_active is not None and "is_active" in cols:
            q = q.filter(TipoEquipoCalefaccion.is_active == is_active)

        # Búsqueda simple por nombre/descripcion si existen
        if search:
            if "nombre" in cols and "descripcion" in cols:
                q = q.filter(
                    (TipoEquipoCalefaccion.nombre.ilike(f"%{search}%"))
                    | (TipoEquipoCalefaccion.descripcion.ilike(f"%{search}%"))
                )
            elif "nombre" in cols:
                q = q.filter(TipoEquipoCalefaccion.nombre.ilike(f"%{search}%"))

        total = q.count()

        # Orden
        if order_by is not None:
            q = q.order_by(order_by)
        elif "nombre" in cols:
            q = q.order_by(TipoEquipoCalefaccion.nombre.asc())

        # Paginación
        page = max(1, int(page or 1))
        page_size = max(1, min(100, int(page_size or 10)))
        items = q.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }

    def get(self, db: Session, id_: int) -> Optional[TipoEquipoCalefaccion]:
        return db.query(TipoEquipoCalefaccion).get(id_)

    # --------------------------
    # Creación
    # --------------------------
    def create(self, db: Session, payload: Any, user: Optional[str] = None) -> TipoEquipoCalefaccion:
        """
        Crea un registro nuevo convirtiendo claves a snake_case y
        seteando created_at/created_by si existen.
        """
        raw = _as_dict(payload)
        normalized = {_to_snake(k): v for k, v in raw.items()}

        cols, _ = _model_field_names(TipoEquipoCalefaccion)

        # Campos de auditoría (si existen en el modelo)
        if "created_at" in cols and "created_at" not in normalized:
            normalized["created_at"] = datetime.now(timezone.utc)
        if "created_by" in cols and user:
            normalized["created_by"] = user
        # Si el modelo tiene is_active y no viene, por defecto True
        if "is_active" in cols and "is_active" not in normalized:
            normalized["is_active"] = True

        # IMPORTANTÍSIMO: filtrar solo campos válidos para evitar el error 'CreatedAt'
        data = _filter_to_model_fields(TipoEquipoCalefaccion, normalized)

        obj = TipoEquipoCalefaccion(**data)
        db.add(obj)

        try:
            db.commit()
            db.refresh(obj)
            return obj
        except SQLAlchemyError:
            db.rollback()
            raise

    # --------------------------
    # Actualización
    # --------------------------
    def update(
        self,
        db: Session,
        id_: int,
        payload: Any,
        user: Optional[str] = None,
    ) -> TipoEquipoCalefaccion:
        obj = self.get(db, id_)
        if not obj:
            raise ValueError(f"TipoEquipoCalefaccion id={id_} no encontrado")

        raw = _as_dict(payload)
        normalized = {_to_snake(k): v for k, v in raw.items()}

        cols, _ = _model_field_names(TipoEquipoCalefaccion)

        # Auditoría de update
        if "updated_at" in cols:
            normalized["updated_at"] = datetime.now(timezone.utc)
        if "updated_by" in cols and user:
            normalized["updated_by"] = user

        data = _filter_to_model_fields(TipoEquipoCalefaccion, normalized)

        for k, v in data.items():
            setattr(obj, k, v)

        try:
            db.commit()
            db.refresh(obj)
            return obj
        except SQLAlchemyError:
            db.rollback()
            raise

    # --------------------------
    # Activar / Desactivar (opcional)
    # --------------------------
    def set_active(self, db: Session, id_: int, active: bool, user: Optional[str] = None) -> TipoEquipoCalefaccion:
        obj = self.get(db, id_)
        if not obj:
            raise ValueError(f"TipoEquipoCalefaccion id={id_} no encontrado")

        cols, _ = _model_field_names(TipoEquipoCalefaccion)
        if "is_active" not in cols:
            raise ValueError("El modelo no tiene columna is_active")

        obj.is_active = bool(active)
        if "updated_at" in cols:
            obj.updated_at = datetime.now(timezone.utc)
        if "updated_by" in cols and user:
            obj.updated_by = user

        try:
            db.commit()
            db.refresh(obj)
            return obj
        except SQLAlchemyError:
            db.rollback()
            raise

    # --------------------------
    # Borrado (soft/hard)
    # --------------------------
    def delete(self, db: Session, id_: int, hard: bool = False, user: Optional[str] = None) -> None:
        obj = self.get(db, id_)
        if not obj:
            return

        cols, _ = _model_field_names(TipoEquipoCalefaccion)

        if not hard and ("is_active" in cols or "deleted_at" in cols):
            # Soft delete
            if "is_active" in cols:
                obj.is_active = False
            if "deleted_at" in cols:
                obj.deleted_at = datetime.now(timezone.utc)
            if "updated_at" in cols:
                obj.updated_at = datetime.now(timezone.utc)
            if "updated_by" in cols and user:
                obj.updated_by = user

            try:
                db.commit()
                return
            except SQLAlchemyError:
                db.rollback()
                raise
        else:
            # Hard delete
            try:
                db.delete(obj)
                db.commit()
            except SQLAlchemyError:
                db.rollback()
                raise


# Instancia reutilizable del servicio
svc = TipoEquipoCalefaccionService()
