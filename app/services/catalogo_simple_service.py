# app/services/catalogo_simple_service.py
from __future__ import annotations
from typing import Type, Any, Iterable
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, literal, and_, or_
from sqlalchemy.exc import IntegrityError

# Se espera que los modelos tengan (Id, Nombre) y opcionalmente:
# CreatedAt, UpdatedAt, DeletedAt, Version, Active, CreatedBy, ModifiedBy
# Notas:
# - Compatible con SQL Server: evitamos "NULLS LAST" en ORDER BY
# - Control de concurrencia optimista via Version (si existe)
# - Filtros seguros para Active (bit/boolean)
# - Búsqueda case-insensitive y con trim
# - Prevención de duplicados por Nombre (case-insensitive)
# - Paginación con límites y metadatos
# - Métodos utilitarios: restore/reactivate, toggle_active, hard_delete, bulk_upsert

MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 20

class CatalogoSimpleService:
    def __init__(self, model: Type, has_audit: bool = False):
        self.model = model
        self.has_audit = has_audit

    # -------------------- Helpers --------------------
    def _now(self) -> datetime:
        return datetime.utcnow()

    def _has(self, attr: str) -> bool:
        return hasattr(self.model, attr)

    def _filter_active(self, query, include_inactive: bool):
        """Filtra por Active==True si corresponde."""
        M = self.model
        if self.has_audit and self._has("Active"):
            if not include_inactive:
                # Soporta bit/boolean en SQL Server
                return query.filter(M.Active == literal(True))
        return query

    def _safe_like(self, col, q: str):
        """LIKE case-insensitive y tolerante a NULL usando COALESCE + lower."""
        like = f"%{(q or '').strip()}%"
        return func.lower(func.coalesce(col, "")).like(func.lower(like))

    def _normalized_nombre(self, nombre: str | None) -> str:
        return (nombre or "").strip()

    def _order_nulls_last(self, *cols):
        """
        Emula NULLS LAST compatible con SQL Server:
        ORDER BY (CASE WHEN col IS NULL THEN 1 ELSE 0 END), col ASC
        """
        ordered = []
        for c in cols:
            ordered.append(case((c.is_(None), 1), else_=0))
            ordered.append(c.asc())
        return ordered

    def _enforce_page(self, page: int | None, page_size: int | None):
        page = max(1, int(page or 1))
        size = int(page_size or DEFAULT_PAGE_SIZE)
        size = min(MAX_PAGE_SIZE, max(1, size))
        return page, size

    def _raise_404(self):
        raise HTTPException(status_code=404, detail="No encontrado")

    def _bump_version(self, obj):
        if self.has_audit and self._has("Version"):
            obj.Version = (getattr(obj, "Version", 0) or 0) + 1

    def _set_audit_on_create(self, data: dict[str, Any]):
        if not self.has_audit:
            return
        now = self._now()
        defaults = {
            "CreatedAt": now,
            "UpdatedAt": now,
            "Version": 1,
            "Active": True,
        }
        for k, v in defaults.items():
            if self._has(k):
                data.setdefault(k, v)
        for fld in ("CreatedBy", "ModifiedBy"):
            if self._has(fld):
                data.setdefault(fld, None)

    def _set_audit_on_update(self, obj):
        if not self.has_audit:
            return
        if self._has("UpdatedAt"):
            obj.UpdatedAt = self._now()
        self._bump_version(obj)

    def _unique_nombre_guard(self, db: Session, nombre: str, exclude_id: int | None = None):
        """
        Previene duplicados en Nombre (case-insensitive, trim). Útil cuando no hay unique index.
        """
        M = self.model
        n = self._normalized_nombre(nombre)
        if not n:
            return
        q = db.query(M.Id).filter(self._safe_like(M.Nombre, n))
        # match exact (case-insensitive) tras normalizar
        q = q.filter(func.trim(func.lower(M.Nombre)) == func.lower(n))
        if exclude_id is not None:
            q = q.filter(M.Id != exclude_id)
        if db.query(q.exists()).scalar():
            raise HTTPException(status_code=409, detail="Ya existe un registro con ese Nombre")

    # -------------------- Listado paginado --------------------
    def list(
        self,
        db: Session,
        q: str | None = None,
        page: int | None = 1,
        page_size: int | None = DEFAULT_PAGE_SIZE,
        include_inactive: bool = False,
        sort_by: str = "Nombre",
        sort_dir: str = "asc",
    ) -> dict:
        M = self.model
        page, page_size = self._enforce_page(page, page_size)

        # Query base
        query = db.query(M)
        query = self._filter_active(query, include_inactive)

        # Búsqueda
        if q:
            query = query.filter(self._safe_like(M.Nombre, q))

        # Total (usa subquery para evitar COUNT con ORDER costly)
        total = db.query(func.count(literal(1))).select_from(query.subquery()).scalar() or 0

        # Orden seguro (whitelist)
        sort_by = (sort_by or "Nombre").strip()
        sort_dir = (sort_dir or "asc").lower()
        valid_cols = {"Id": M.Id}
        if self._has("Nombre"):
            valid_cols["Nombre"] = M.Nombre
        # Si el modelo tiene "Codigo", habilita orden por Codigo
        if self._has("Codigo"):
            valid_cols["Codigo"] = getattr(M, "Codigo")

        col = valid_cols.get(sort_by, M.Nombre if "Nombre" in valid_cols else M.Id)

        # Emular NULLS LAST y dirección
        order_clause = self._order_nulls_last(col, M.Id)
        if sort_dir == "desc":
            # invertimos la dirección manteniendo nulls al final
            order_clause = [order_clause[0].desc()] + [c.desc() if hasattr(c, "desc") else c for c in order_clause[1:]]

        items = (
            query.order_by(*order_clause)
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )

        last_page = (total + page_size - 1) // page_size if page_size else 1
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "last_page": max(1, last_page),
            "has_next": page < last_page,
            "has_prev": page > 1,
            "items": items,
        }

    # -------------------- Select liviano (Id, Nombre) --------------------
    def list_select(self, db: Session, q: str | None = None, limit: int = 50):
        M = self.model
        query = db.query(M.Id, M.Nombre)
        query = self._filter_active(query, include_inactive=False)
        if q:
            query = query.filter(self._safe_like(M.Nombre, q))

        # Orden estable y compatible
        items = (
            query.order_by(*self._order_nulls_last(M.Nombre, M.Id))
                 .limit(max(1, min(limit, 500)))
                 .all()
        )
        # Devuelve lista de dicts livianos
        return [{"Id": r[0], "Nombre": r[1]} for r in items]

    # -------------------- Get --------------------
    def get(self, db: Session, id: int):
        M = self.model
        obj = db.query(M).filter(M.Id == id).first()
        if not obj:
            self._raise_404()
        return obj

    # -------------------- Create --------------------
    def create(self, db: Session, payload):
        M = self.model
        data = payload.model_dump(exclude_unset=True)
        # Normaliza y valida Nombre duplicado
        if self._has("Nombre") and "Nombre" in data:
            data["Nombre"] = self._normalized_nombre(data["Nombre"])
            self._unique_nombre_guard(db, data["Nombre"])

        self._set_audit_on_create(data)

        obj = M(**data)
        db.add(obj)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # fallback si hay unique index
            raise HTTPException(status_code=409, detail="Conflicto de clave única")
        db.refresh(obj)
        return obj

    # -------------------- Update --------------------
    def update(self, db: Session, id: int, payload, expected_version: int | None = None):
        """
        Si 'Version' existe y expected_version no es None, aplica control optimista.
        """
        M = self.model
        obj = self.get(db, id)

        if expected_version is not None and self._has("Version"):
            if (obj.Version or 0) != expected_version:
                raise HTTPException(status_code=412, detail="Versión desactualizada")

        data = payload.model_dump(exclude_unset=True)

        # Normaliza y valida duplicados de Nombre
        if self._has("Nombre") and "Nombre" in data:
            data["Nombre"] = self._normalized_nombre(data["Nombre"])
            self._unique_nombre_guard(db, data["Nombre"], exclude_id=id)

        for k, v in data.items():
            setattr(obj, k, v)

        self._set_audit_on_update(obj)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Conflicto de clave única")
        db.refresh(obj)
        return obj

    # -------------------- Delete (soft si has_audit) --------------------
    def delete(self, db: Session, id: int):
        M = self.model
        obj = self.get(db, id)
        if self.has_audit and self._has("Active"):
            # Soft delete
            if getattr(obj, "Active", True) is False:
                return  # ya inactivo
            obj.Active = False
            if self._has("DeletedAt"):
                obj.DeletedAt = self._now()
            self._set_audit_on_update(obj)
            db.commit()
            return
        # Hard delete si no hay auditoría
        db.delete(obj)
        db.commit()

    # -------------------- Hard delete explícito --------------------
    def hard_delete(self, db: Session, id: int):
        obj = self.get(db, id)
        db.delete(obj)
        db.commit()

    # -------------------- Reactivar (undo soft delete) --------------------
    def restore(self, db: Session, id: int):
        M = self.model
        if not (self.has_audit and self._has("Active")):
            raise HTTPException(status_code=400, detail="El modelo no soporta restauración")
        obj = self.get(db, id)
        obj.Active = True
        if self._has("DeletedAt"):
            obj.DeletedAt = None
        self._set_audit_on_update(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # -------------------- Toggle Active --------------------
    def toggle_active(self, db: Session, id: int, active: bool):
        M = self.model
        if not (self.has_audit and self._has("Active")):
            raise HTTPException(status_code=400, detail="El modelo no soporta Active")
        obj = self.get(db, id)
        obj.Active = bool(active)
        if not obj.Active and self._has("DeletedAt"):
            obj.DeletedAt = self._now()
        elif obj.Active and self._has("DeletedAt"):
            obj.DeletedAt = None
        self._set_audit_on_update(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # -------------------- Bulk Upsert (por Nombre) --------------------
    def bulk_upsert(self, db: Session, rows: Iterable[dict[str, Any]]):
        """
        Inserta/actualiza por 'Nombre' normalizado. Útil para catálogos.
        """
        M = self.model
        now = self._now()
        created, updated = 0, 0

        for r in rows:
            data = dict(r)
            nombre = self._normalized_nombre(data.get("Nombre"))
            if not nombre:
                continue

            existing = (
                db.query(M)
                .filter(func.trim(func.lower(M.Nombre)) == func.lower(nombre))
                .first()
            )
            if existing:
                # update
                for k, v in data.items():
                    if k == "Id":
                        continue
                    setattr(existing, k, v if k != "Nombre" else nombre)
                if self.has_audit:
                    if self._has("Active") and getattr(existing, "Active", True) is False:
                        existing.Active = True
                    self._set_audit_on_update(existing)
                updated += 1
            else:
                # create
                payload = {"Nombre": nombre, **{k: v for k, v in data.items() if k != "Nombre"}}
                self._set_audit_on_create(payload)
                obj = M(**payload)
                db.add(obj)
                created += 1

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Conflicto de clave única en bulk_upsert")

        return {"created": created, "updated": updated}
