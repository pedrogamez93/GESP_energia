# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Iterable

from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.exc import SQLAlchemyError

# Ajusta este import a tu estructura real de modelos
from app.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion


def _to_snake(name: str) -> str:
    """
    Convierte CamelCase/PascalCase a snake_case.
    Ej: CreatedAt -> created_at ; Nombre -> nombre
    """
    out, prev_lower = [], False
    prev_char = ""
    for ch in name or "":
        if ch.isupper() and (prev_lower or (prev_char and prev_char.isalpha())):
            out.append("_")
        out.append(ch.lower())
        prev_lower = ch.islower()
        prev_char = ch
    return "".join(out)


def _only_model_fields(model, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filtra el dict dejando únicamente claves que existen en el modelo
    (columnas y relaciones). Evita TypeError por kwargs inválidos.
    """
    mapper = sa_inspect(model)
    cols = {attr.key for attr in mapper.attrs if hasattr(attr, "columns")}
    rels = {rel.key for rel in mapper.relationships}
    allowed = cols | rels
    return {k: v for k, v in data.items() if k in allowed}


def _normalize_payload(payload: Any) -> Dict[str, Any]:
    """
    Acepta BaseModel v2, BaseModel v1 o dict. Convierte claves a snake_case.
    """
    if hasattr(payload, "model_dump"):  # Pydantic v2
        raw = payload.model_dump(exclude_unset=True)
    elif hasattr(payload, "dict"):  # Pydantic v1
        raw = payload.dict(exclude_unset=True)
    elif isinstance(payload, dict):
        raw = dict(payload)
    else:
        raise TypeError("payload debe ser dict o Pydantic BaseModel")

    return {_to_snake(k): v for k, v in raw.items()}


class TipoEquipoCalefaccionService:
    """
    Servicio CRUD para TipoEquipoCalefaccion con:
    - Normalización de claves (Camel/Pascal -> snake_case)
    - Auditoría created_at/created_by/updated_at/updated_by
    - Filtrado estricto de campos válidos del modelo
    """

    # ---------- READ ----------
    def get(self, db: Session, id_: int) -> Optional[TipoEquipoCalefaccion]:
        return db.get(TipoEquipoCalefaccion, id_)

    def list(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        only_active: Optional[bool] = None,
        order_by: Optional[Iterable[Any]] = None,
    ) -> list[TipoEquipoCalefaccion]:
        q = db.query(TipoEquipoCalefaccion)
        if only_active is True:
            if "is_active" in {c.key for c in sa_inspect(TipoEquipoCalefaccion).attrs if hasattr(c, "columns")}:
                q = q.filter(TipoEquipoCalefaccion.is_active.is_(True))
        if order_by:
            q = q.order_by(*order_by)
        return q.offset(skip).limit(limit).all()

    # ---------- CREATE ----------
    def create(self, db: Session, payload: Any, user: Optional[str] = None) -> TipoEquipoCalefaccion:
        normalized = _normalize_payload(payload)

        # Auditoría si existen esas columnas
        cols = {c.key for c in sa_inspect(TipoEquipoCalefaccion).attrs if hasattr(c, "columns")}
        if "created_at" in cols and "created_at" not in normalized:
            normalized["created_at"] = datetime.now(timezone.utc)
        if "created_by" in cols and user:
            normalized["created_by"] = user
        if "is_active" in cols and "is_active" not in normalized:
            normalized["is_active"] = True

        data = _only_model_fields(TipoEquipoCalefaccion, normalized)

        obj = TipoEquipoCalefaccion(**data)  # ← ya no pasará kwargs inválidos (e.g., CreatedAt)
        db.add(obj)
        try:
            db.commit()
            db.refresh(obj)
            return obj
        except SQLAlchemyError:
            db.rollback()
            raise

    # ---------- UPDATE ----------
    def update(self, db: Session, id_: int, payload: Any, user: Optional[str] = None) -> TipoEquipoCalefaccion:
        obj = self.get(db, id_)
        if not obj:
            raise ValueError(f"TipoEquipoCalefaccion id={id_} no encontrado")

        normalized = _normalize_payload(payload)

        cols = {c.key for c in sa_inspect(TipoEquipoCalefaccion).attrs if hasattr(c, "columns")}
        if "updated_at" in cols:
            normalized["updated_at"] = datetime.now(timezone.utc)
        if "updated_by" in cols and user:
            normalized["updated_by"] = user

        data = _only_model_fields(TipoEquipoCalefaccion, normalized)

        for k, v in data.items():
            setattr(obj, k, v)

        try:
            db.commit()
            db.refresh(obj)
            return obj
        except SQLAlchemyError:
            db.rollback()
            raise

    # ---------- DELETE ----------
    def delete(self, db: Session, id_: int) -> None:
        obj = self.get(db, id_)
        if not obj:
            return
        db.delete(obj)
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise

    # ---------- ACTIVATE / DEACTIVATE ----------
    def set_active(self, db: Session, id_: int, active: bool, user: Optional[str] = None) -> TipoEquipoCalefaccion:
        obj = self.get(db, id_)
        if not obj:
            raise ValueError(f"TipoEquipoCalefaccion id={id_} no encontrado")

        cols = {c.key for c in sa_inspect(TipoEquipoCalefaccion).attrs if hasattr(c, "columns")}
        if "is_active" in cols:
            obj.is_active = active
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


# Instancia reusable del servicio
svc_tipo_equipo_calefaccion = TipoEquipoCalefaccionService()
