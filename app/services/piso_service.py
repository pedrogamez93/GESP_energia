# app/services/piso_service.py
from __future__ import annotations
from datetime import datetime
from typing import Tuple, List, Optional, Set, Any

from sqlalchemy import func, text, case  # 👈 añadimos `case`
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect as sa_inspect
from fastapi import HTTPException

from app.db.models.piso import Piso
from app.schemas.pisos import PisoDTO, PisoListDTO, PisoCreate, PisoUpdate


# =========================
#      HELPERS INTERNOS
# =========================

def _model_columns(model_cls: Any) -> Set[str]:
    """
    Devuelve los nombres de atributos mapeados válidos para el modelo.
    Sirve para filtrar el payload y evitar TypeError por kwargs inválidos.
    """
    try:
        mapper = sa_inspect(model_cls)
        return {prop.key for prop in mapper.attrs}
    except Exception:
        return set()

_PISO_COLS = _model_columns(Piso)


def _resolve_numero_piso_id(db: Session, numero: Optional[str | int]) -> Optional[int]:
    """
    Acepta:
      - int / str numérico -> se castea a int.
      - str texto -> busca en dbo.NumeroPisos por Nombre/Numero y devuelve Id.
    Devuelve None si no hay nada que resolver.
    """
    if numero is None or str(numero).strip() == "":
        return None

    # ¿Viene como número?
    try:
        return int(numero)  # "3" -> 3
    except Exception:
        pass

    # Buscar por nombre (o por alguna columna de texto que tengas)
    s = str(numero).strip()
    row = db.execute(
        text("""
            SELECT TOP 1 Id
            FROM dbo.NumeroPisos
            WHERE Nombre = :s OR Numero = :s
        """),
        {"s": s},
    ).first()

    if row:
        return int(row[0])

    # No encontrado: señalamos error claro (mejor que insertar NULL en NOT NULL)
    raise HTTPException(
        status_code=400,
        detail=f"No existe un NumeroPiso con nombre/numero '{s}' en dbo.NumeroPisos"
    )


def _filter_kwargs_for_model(kwargs: dict) -> dict:
    """Elimina del dict cualquier clave que Piso no conozca."""
    return {k: v for k, v in kwargs.items() if k in _PISO_COLS}


def _order_clause_or_id():
    """
    Devuelve la/s columnas de orden:
      - Si existe Piso.Orden, hacemos NULLS LAST compatible con SQL Server:
        ORDER BY CASE WHEN Orden IS NULL THEN 1 ELSE 0 END, Orden ASC
      - Luego siempre Id ASC para estabilidad.
    """
    cols = []
    if hasattr(Piso, "Orden"):
        # ✅ SQL Server-friendly NULLS LAST:
        nulls_last = case((Piso.Orden.is_(None), 1), else_=0).asc()
        cols.extend([nulls_last, Piso.Orden.asc()])
    # Siempre agregamos Id al final para orden estable
    cols.append(Piso.Id.asc())
    return cols


# =========================
#        SERVICIO
# =========================

class PisoService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- LISTADO ----------
    def list_paged(
        self,
        page: int = 1,
        page_size: int = 50,
        division_id: Optional[int] = None,
        active: Optional[bool] = True,
    ) -> Tuple[int, List[Piso]]:
        q = self.db.query(Piso)
        if active is not None and "Active" in _PISO_COLS:
            q = q.filter(Piso.Active == active)
        if division_id is not None and "DivisionId" in _PISO_COLS:
            q = q.filter(Piso.DivisionId == division_id)

        total = q.count()
        size = max(1, min(200, page_size))

        q = q.order_by(*_order_clause_or_id())
        items = q.offset((page - 1) * size).limit(size).all()
        return total, items

    def list_by_division(self, division_id: int, active: Optional[bool] = True) -> List[Piso]:
        q = self.db.query(Piso)
        if "DivisionId" in _PISO_COLS:
            q = q.filter(Piso.DivisionId == division_id)
        if active is not None and "Active" in _PISO_COLS:
            q = q.filter(Piso.Active == active)
        return q.order_by(*_order_clause_or_id()).all()

    # ---------- DETALLE ----------
    def get(self, piso_id: int) -> Piso | None:
        return self.db.query(Piso).filter(Piso.Id == piso_id).first()

    # ---------- CREATE ----------
    def create(self, data: PisoCreate, created_by: str) -> Piso:
        """
        - Mapea payload.Numero / payload.Nombre -> NumeroPisoId
        - Filtra kwargs a columnas válidas del modelo
        - Completa metadatos obligatorios
        """
        now = datetime.utcnow()

        payload = data.model_dump(exclude_unset=True)

        # Resolver NumeroPisoId desde Numero/Nombre
        numero_val = payload.pop("Numero", None)
        nombre_val = payload.pop("Nombre", None)
        numero_piso_id = _resolve_numero_piso_id(self.db, numero_val or nombre_val)

        kwargs = dict(payload)

        if numero_piso_id is not None and "NumeroPisoId" in _PISO_COLS:
            kwargs["NumeroPisoId"] = numero_piso_id

        # Defaults de dominio si faltan (la BD los exige como NOT NULL)
        if "Superficie" in _PISO_COLS and "Superficie" not in kwargs:
            kwargs["Superficie"] = 0
        if "Altura" in _PISO_COLS and "Altura" not in kwargs:
            kwargs["Altura"] = 0

        # Metadatos obligatorios
        if "CreatedAt" in _PISO_COLS:
            kwargs["CreatedAt"] = now
        if "UpdatedAt" in _PISO_COLS:
            kwargs["UpdatedAt"] = now
        if "Version" in _PISO_COLS and "Version" not in kwargs:
            kwargs["Version"] = 1
        if "Active" in _PISO_COLS and "Active" not in kwargs:
            kwargs["Active"] = True
        if "CreatedBy" in _PISO_COLS:
            kwargs["CreatedBy"] = created_by
        if "ModifiedBy" in _PISO_COLS:
            kwargs["ModifiedBy"] = created_by

        # Filtrar cualquier campo no mapeado
        kwargs = _filter_kwargs_for_model(kwargs)

        try:
            obj = Piso(**kwargs)
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
            return obj
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Error de integridad al crear Piso: {str(e.orig)}"
            )

    # ---------- UPDATE (ADMIN) ----------
    def update_admin(self, piso_id: int, data: PisoUpdate, modified_by: str) -> Piso | None:
        obj = self.get(piso_id)
        if not obj:
            return None

        now = datetime.utcnow()
        payload = data.model_dump(exclude_unset=True)

        # Si viene Numero/Nombre, recalculamos NumeroPisoId
        needs_numero = ("Numero" in payload) or ("Nombre" in payload)
        if needs_numero:
            numero_val = payload.pop("Numero", None)
            nombre_val = payload.pop("Nombre", None)
            numero_piso_id = _resolve_numero_piso_id(self.db, numero_val or nombre_val)
            if numero_piso_id is not None and "NumeroPisoId" in _PISO_COLS:
                setattr(obj, "NumeroPisoId", numero_piso_id)

        # Seteo de campos válidos
        cleaned = _filter_kwargs_for_model(payload)
        for k, v in cleaned.items():
            setattr(obj, k, v)

        # Metadatos
        if "UpdatedAt" in _PISO_COLS:
            obj.UpdatedAt = now
        if "ModifiedBy" in _PISO_COLS:
            obj.ModifiedBy = modified_by
        if "Version" in _PISO_COLS:
            obj.Version = (obj.Version or 0) + 1

        self.db.commit()
        self.db.refresh(obj)
        return obj

    # ---------- SOFT-DELETE ----------
    def soft_delete(self, piso_id: int, modified_by: str) -> Piso | None:
        obj = self.get(piso_id)
        if not obj:
            return None
        if "Active" in _PISO_COLS and not obj.Active:
            return obj

        now = datetime.utcnow()
        if "Active" in _PISO_COLS:
            obj.Active = False
        if "UpdatedAt" in _PISO_COLS:
            obj.UpdatedAt = now
        if "ModifiedBy" in _PISO_COLS:
            obj.ModifiedBy = modified_by
        if "Version" in _PISO_COLS:
            obj.Version = (obj.Version or 0) + 1

        self.db.commit()
        self.db.refresh(obj)
        return obj
