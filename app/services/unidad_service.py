# app/services/unidad_service.py
from __future__ import annotations
from typing import List, Optional, Tuple
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models.unidad import Unidad, UnidadInmueble

from app.schemas.unidad import (
    UnidadDTO,
    UnidadListDTO,
    UnidadFilterDTO,
    InmuebleTopDTO,
    pisoDTO,
    AreaDTO,
)
from app.schemas.pagination import Page, PageMeta


# ---------------------- Helpers ----------------------
_ACTIVE_CANDIDATES = ("Active", "Activo", "IsActive", "Enabled")

def _now() -> datetime:
    return datetime.now()

def _find_active_column(model) -> Tuple[Optional[str], Optional[object]]:
    for name in _ACTIVE_CANDIDATES:
        if hasattr(model, name):
            return name, getattr(model, name)
    return None, None

_ACTIVE_NAME, _ACTIVE_COL = _find_active_column(Unidad)

def _get_instance_active(u: Unidad) -> Optional[bool]:
    if _ACTIVE_NAME:
        return getattr(u, _ACTIVE_NAME)
    return None

def _set_instance_active(u: Unidad, value: bool) -> None:
    if _ACTIVE_NAME:
        setattr(u, _ACTIVE_NAME, value)

def _q_only_actives(q):
    if _ACTIVE_COL is not None:
        # En MSSQL es mejor "col = 1" que "IS TRUE"
        return q.filter(_ACTIVE_COL == True)  # noqa: E712
    return q

def _coerce_boolish_to_int(v) -> int | None:
    """Convierte 'Si/No', True/False, '1'/'0' → 1/0/None."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return 1 if v else 0
    s = str(v).strip().lower()
    if s in {"1", "si", "sí", "true", "t", "y", "yes"}:
        return 1
    if s in {"0", "no", "false", "f", "n"}:
        return 0
    try:
        return int(s)
    except Exception:
        return None

def _map_unidad_to_dto(u: Unidad) -> UnidadDTO:
    active_val = _get_instance_active(u)
    return UnidadDTO.model_validate(
        {
            "Id": u.Id,
            "OldId": u.OldId,
            "Nombre": u.Nombre,
            "ServicioId": u.ServicioId or 0,
            "ServicioNombre": None,
            "InstitucionNombre": None,
            "Active": "1" if (active_val if active_val is not None else True) else "0",
            "Funcionarios": u.Funcionarios or 0,
            "ReportaPMG": bool(getattr(u, "ReportaPMG", False)),
            "IndicadorEE": bool(getattr(u, "IndicadorEE", False)),
            "AccesoFactura": getattr(u, "AccesoFactura", 0) or 0,
            "InstitucionResponsableId": getattr(u, "InstitucionResponsableId", None),
            "ServicioResponsableId": getattr(u, "ServicioResponsableId", None),
            "OrganizacionResponsable": getattr(u, "OrganizacionResponsable", None),
            "Servicio": None,
            "Inmuebles": [],
            "Pisos": [],
            "Areas": [],
        },
        from_attributes=False,
    )

def _map_unidad_to_listdto(
    u: Unidad,
    institucion_nombre: Optional[str] = None,
    servicio_nombre: Optional[str] = None,
) -> UnidadListDTO:
    active_val = _get_instance_active(u)
    return UnidadListDTO.model_validate(
        {
            "Id": u.Id,
            "OldId": u.OldId,
            "Nombre": u.Nombre,
            "Ubicacion": None,
            "InstitucionId": getattr(u, "InstitucionResponsableId", 0) or 0,
            "InstitucionNombre": institucion_nombre or "",
            "ServicioId": u.ServicioId or 0,
            "ServicioNombre": servicio_nombre or "",
            "Active": "1" if (active_val if active_val is not None else True) else "0",
            "Funcionarios": u.Funcionarios or 0,
            "ReportaPMG": bool(getattr(u, "ReportaPMG", False)),
            "IndicadorEE": bool(getattr(u, "IndicadorEE", False)),
            "AccesoFactura": "1" if (getattr(u, "AccesoFactura", 0) or 0) > 0 else "0",
            "InstitucionResponsableId": getattr(u, "InstitucionResponsableId", None),
            "InstitucionResponsableNombre": institucion_nombre,
            "ServicioResponsableId": getattr(u, "ServicioResponsableId", None),
            "ServicioResponsableNombre": servicio_nombre,
            "OrganizacionResponsable": getattr(u, "OrganizacionResponsable", None),
        },
        from_attributes=False,
    )

def _lazy_models():
    """
    Importa UnidadPiso y UnidadArea SOLO si existen en tu proyecto
    (para no romper el arranque si están en otro módulo o no existen).
    """
    UnidadPiso = None
    UnidadArea = None
    try:
        from app.db.models.unidad_piso import UnidadPiso as _UP  # type: ignore
        UnidadPiso = _UP
    except Exception:
        try:
            # por si los tienes en el mismo archivo 'unidad.py' (poco probable)
            from app.db.models.unidad import UnidadPiso as _UP  # type: ignore
            UnidadPiso = _UP
        except Exception:
            UnidadPiso = None
    try:
        from app.db.models.unidad_area import UnidadArea as _UA  # type: ignore
        UnidadArea = _UA
    except Exception:
        try:
            from app.db.models.unidad import UnidadArea as _UA  # type: ignore
            UnidadArea = _UA
        except Exception:
            UnidadArea = None
    return UnidadPiso, UnidadArea


# ---------------------- Servicio ----------------------
class UnidadService:
    """Replica de GobEfi.Web.Services.UnidadService (lógica esencial)."""

    def __init__(self, db: Session, current_user_id: Optional[str], current_user_is_admin: bool):
        self.db = db
        self.current_user_id = current_user_id
        self.current_user_is_admin = current_user_is_admin

    # ---------- CREATE ----------
    def create(self, payload: dict) -> UnidadDTO:
        """
        FIX:
        - ChkNombre: si no viene, se fuerza a 1 (BD no acepta NULL).
        - AccesoFactura: normalizado a 0/1.
        - Altas en pivotes protegidas con import perezoso.
        """
        chk_nombre = payload.get("ChkNombre")
        if chk_nombre is None:
            chk_nombre = 1  # valor seguro para cumplir NOT NULL

        acceso_factura = _coerce_boolish_to_int(payload.get("AccesoFactura"))

        try:
            u = Unidad(
                **({_ACTIVE_NAME: True} if _ACTIVE_NAME else {}),
                CreatedAt=_now(),
                UpdatedAt=_now(),
                CreatedBy=self.current_user_id,
                Version=1,

                Nombre=payload.get("Nombre"),
                ServicioId=payload.get("ServicioId"),
                ChkNombre=chk_nombre,
                Funcionarios=payload.get("Funcionarios"),
                ReportaPMG=payload.get("ReportaPMG") or False,
                IndicadorEE=payload.get("IndicadorEE") or False,
                AccesoFactura=acceso_factura,
                InstitucionResponsableId=payload.get("InstitucionResponsableId"),
                ServicioResponsableId=payload.get("ServicioResponsableId"),
                OrganizacionResponsable=payload.get("OrganizacionResponsable"),
            )
            self.db.add(u)
            self.db.flush()  # obtener u.Id

            UnidadPiso, UnidadArea = _lazy_models()

            inmuebles = payload.get("Inmuebles") or []
            if inmuebles:
                root = inmuebles[0]
                if root.get("Id"):
                    self.db.add(UnidadInmueble(UnidadId=u.Id, InmuebleId=root["Id"]))

                for edif in (root.get("Edificios") or []):
                    if edif.get("Id"):
                        self.db.add(UnidadInmueble(UnidadId=u.Id, InmuebleId=edif["Id"]))

                    for piso in (edif.get("Pisos") or []):
                        if UnidadPiso is not None and piso.get("Id"):
                            self.db.add(UnidadPiso(UnidadId=u.Id, PisoId=piso["Id"]))
                        for area in (piso.get("Areas") or []):
                            if UnidadArea is not None and area.get("Id"):
                                self.db.add(UnidadArea(UnidadId=u.Id, AreaId=area["Id"]))

            self.db.commit()
            self.db.refresh(u)
            return _map_unidad_to_dto(u)

        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Error de integridad al crear Unidad (NOT NULL/constraint): {str(e.orig)}")

    # ---------- UPDATE ----------
    def update(self, unidad_id: int, payload: dict) -> None:
        u = self.db.get(Unidad, unidad_id)
        if not u or (_ACTIVE_NAME and not getattr(u, _ACTIVE_NAME)):
            raise ValueError("Unidad no encontrada o inactiva")

        u.OldId = payload.get("OldId")
        u.Nombre = payload.get("Nombre", u.Nombre)
        u.ServicioId = payload.get("ServicioId", u.ServicioId)
        u.Funcionarios = payload.get("Funcionarios", u.Funcionarios)

        if "ReportaPMG" in payload:
            u.ReportaPMG = payload.get("ReportaPMG")
        if "IndicadorEE" in payload:
            u.IndicadorEE = payload.get("IndicadorEE")
        if "AccesoFactura" in payload:
            u.AccesoFactura = _coerce_boolish_to_int(payload.get("AccesoFactura"))

        # Sanear/actualizar ChkNombre
        if "ChkNombre" in payload and payload.get("ChkNombre") is not None:
            u.ChkNombre = int(payload.get("ChkNombre") or 1)
        elif u.ChkNombre is None:
            u.ChkNombre = 1

        u.InstitucionResponsableId = payload.get("InstitucionResponsableId", getattr(u, "InstitucionResponsableId", None))
        u.ServicioResponsableId = payload.get("ServicioResponsableId", getattr(u, "ServicioResponsableId", None))
        u.OrganizacionResponsable = payload.get("OrganizacionResponsable", getattr(u, "OrganizacionResponsable", None))

        u.UpdatedAt = _now()
        u.ModifiedBy = self.current_user_id
        u.Version = (u.Version or 0) + 1

        # Limpia puentes y vuelve a crear según payload (si existen los modelos)
        UnidadPiso, UnidadArea = _lazy_models()
        self.db.query(UnidadInmueble).filter_by(UnidadId=unidad_id).delete()
        if UnidadPiso is not None:
            self.db.query(UnidadPiso).filter_by(UnidadId=unidad_id).delete()
        if UnidadArea is not None:
            self.db.query(UnidadArea).filter_by(UnidadId=unidad_id).delete()

        inmuebles = payload.get("Inmuebles") or []
        if inmuebles:
            root = inmuebles[0]
            if root.get("Id"):
                self.db.add(UnidadInmueble(UnidadId=unidad_id, InmuebleId=root["Id"]))

            for edif in (root.get("Edificios") or []):
                if edif.get("Id"):
                    self.db.add(UnidadInmueble(UnidadId=unidad_id, InmuebleId=edif["Id"]))

                for piso in (edif.get("Pisos") or []):
                    if UnidadPiso is not None and piso.get("Id"):
                        self.db.add(UnidadPiso(UnidadId=unidad_id, PisoId=piso["Id"]))
                    for area in (piso.get("Areas") or []):
                        if UnidadArea is not None and area.get("Id"):
                            self.db.add(UnidadArea(UnidadId=unidad_id, AreaId=area["Id"]))

        self.db.commit()

    # ---------- DELETE (soft) ----------
    def delete(self, unidad_id: int) -> None:
        u = self.db.get(Unidad, unidad_id)
        if not u:
            return
        _set_instance_active(u, False)

        UnidadPiso, UnidadArea = _lazy_models()
        if UnidadArea is not None:
            self.db.query(UnidadArea).filter_by(UnidadId=unidad_id).delete()
        if UnidadPiso is not None:
            self.db.query(UnidadPiso).filter_by(UnidadId=unidad_id).delete()
        self.db.query(UnidadInmueble).filter_by(UnidadId=unidad_id).delete()

        self.db.commit()

    # ---------- GET detalle ----------
    def get(self, unidad_id: int) -> UnidadDTO:
        u = self.db.get(Unidad, unidad_id)
        if not u or (_ACTIVE_NAME and not getattr(u, _ACTIVE_NAME)):
            raise ValueError("Unidad no encontrada o inactiva")

        dto = _map_unidad_to_dto(u)

        inm_ids = [
            r.InmuebleId
            for r in self.db.scalars(
                select(UnidadInmueble).where(UnidadInmueble.UnidadId == unidad_id)
            ).all()
        ]
        dto.Inmuebles = [InmuebleTopDTO(Id=i, TipoInmueble=0) for i in inm_ids]

        # Estas listas se devuelven vacías si no tienes los modelos/puentes
        UnidadPiso, UnidadArea = _lazy_models()

        if UnidadPiso is not None:
            piso_ids = [
                r.PisoId
                for r in self.db.scalars(
                    select(UnidadPiso).where(UnidadPiso.UnidadId == unidad_id)
                ).all()
            ]
            dto.Pisos = [pisoDTO(Id=p, NumeroPisoNombre=None, Checked=True) for p in piso_ids]

        if UnidadArea is not None:
            area_ids = [
                r.AreaId
                for r in self.db.scalars(
                    select(UnidadArea).where(UnidadArea.UnidadId == unidad_id)
                ).all()
            ]
            dto.Areas = [AreaDTO(Id=a, Nombre=None) for a in area_ids]

        return dto

    # ---------- LIST (filter + pagination) ----------
    def list_filter(self, f: UnidadFilterDTO, page: int, page_size: int) -> Page[UnidadListDTO]:
        q = self.db.query(Unidad)
        q = _q_only_actives(q)

        if f.Unidad:
            like = f"%{f.Unidad}%"
            q = q.filter(Unidad.Nombre.ilike(like))

        if f.ServicioId:
            q = q.filter(Unidad.ServicioId == f.ServicioId)
        if f.InstitucionId:
            q = q.filter(Unidad.InstitucionResponsableId == f.InstitucionId)

        if f.RegionId:
            sql = text(
                """
                SELECT DISTINCT ui.UnidadId
                FROM dbo.UnidadesInmuebles ui
                JOIN dbo.Divisiones d ON d.Id = ui.InmuebleId
                JOIN dbo.Direcciones di ON di.Id = d.DireccionId
                WHERE di.RegionId = :region_id
                """
            )
            ids = [row[0] for row in self.db.execute(sql, {"region_id": f.RegionId}).all()]
            if ids:
                q = q.filter(Unidad.Id.in_(ids))
            else:
                q = q.filter(False)

        total: int = q.count()
        items: List[Unidad] = (
            q.order_by(Unidad.Nombre)
             .offset((page - 1) * page_size)
             .limit(page_size)
             .all()
        )

        data = [_map_unidad_to_listdto(u) for u in items]
        pages = (total + page_size - 1) // page_size
        return Page[UnidadListDTO](data=data, meta=PageMeta(total=total, page=page, page_size=page_size, pages=pages))

    # ---------- Asociados por usuario ----------
    def list_asociados_by_user(self, user_id: str) -> List[UnidadListDTO]:
        q = self.db.query(Unidad)
        if not self.current_user_is_admin:
            sql = text(
                """
                SELECT DISTINCT uu.UnidadId
                FROM dbo.UsuarioUnidades uu
                WHERE uu.UsuarioId = :user_id
                """
            )
            ids = [row[0] for row in self.db.execute(sql, {"user_id": user_id}).all()]
            if ids:
                q = q.filter(Unidad.Id.in_(ids))
            else:
                return []

        q = _q_only_actives(q)
        items = q.order_by(Unidad.Nombre).all()
        return [_map_unidad_to_listdto(u) for u in items]

    # ---------- Compatibilidad ----------
    def check_nombre(self, nombre: str, servicio_id: int) -> bool:
        q = self.db.query(Unidad).filter(
            Unidad.Nombre == nombre,
            Unidad.ServicioId == servicio_id,
        )
        q = _q_only_actives(q)
        return bool(q.first())

    def has_inteligent_measurement(self, old_id: int) -> bool:
        found = self.db.query(Unidad).filter(Unidad.OldId == old_id).first()
        return bool(found)
