# app/services/unidad_service.py
from __future__ import annotations

from typing import List, Optional, Tuple
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models.unidad import Unidad  # y UnidadInmueble si lo usas en otros lados

from app.schemas.unidad import (
    UnidadDTO,
    UnidadListDTO,
    UnidadFilterDTO,
    InmuebleTopDTO,
    pisoDTO,
    AreaDTO,
    LinkResult,
    UnidadWithInmueblesDTO,
)
from app.schemas.inmuebles import InmuebleDTO
from app.schemas.pagination import Page, PageMeta

from app.services.inmueble_service import InmuebleService


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


def _q_filter_active(q, active: Optional[int]):
    """
    active:
      - None => ambos (no filtra)
      - 1    => solo activos
      - 0    => solo inactivos
    """
    if _ACTIVE_COL is None:
        return q

    if active is None:
        return q

    a = _coerce_boolish_to_int(active)
    if a == 1:
        return q.filter(_ACTIVE_COL == True)  # noqa: E712
    if a == 0:
        return q.filter(_ACTIVE_COL == False)  # noqa: E712
    return q


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
    (para no romper si están en otro lado o no existen).
    """
    UnidadPiso = None
    UnidadArea = None

    try:
        from app.db.models.unidad_piso import UnidadPiso as _UP  # type: ignore
        UnidadPiso = _UP
    except Exception:
        try:
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
    """Replica de lógica esencial del servicio de Unidades."""

    def __init__(self, db: Session, current_user_id: Optional[str], current_user_is_admin: bool):
        self.db = db
        self.current_user_id = current_user_id
        self.current_user_is_admin = current_user_is_admin

    # ---------- CREATE ----------
    def create(self, payload: dict) -> UnidadDTO:
        chk_nombre = payload.get("ChkNombre")
        if chk_nombre is None:
            chk_nombre = 1

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
            self.db.flush()

            # NOTA: si tu create también necesita poblar UnidadesInmuebles / UnidadesPisos / UnidadesAreas,
            # lo dejamos como lo tenías (si ya lo estás usando).
            self.db.commit()
            self.db.refresh(u)
            return _map_unidad_to_dto(u)

        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Error de integridad al crear Unidad: {str(e.orig)}")

    # ---------- UPDATE ----------
    def update(self, unidad_id: int, payload: dict) -> None:
        u = self.db.get(Unidad, unidad_id)
        if not u:
            raise ValueError("Unidad no encontrada")

        incoming_active: Optional[bool] = None
        if "Active" in payload:
            a = _coerce_boolish_to_int(payload.get("Active"))
            if a is not None:
                incoming_active = bool(a)

        if _ACTIVE_NAME and not getattr(u, _ACTIVE_NAME) and incoming_active is not True:
            raise ValueError("Unidad no encontrada o inactiva")

        if "OldId" in payload:
            u.OldId = payload.get("OldId")
        if "Nombre" in payload:
            u.Nombre = payload.get("Nombre")
        if "ServicioId" in payload:
            u.ServicioId = payload.get("ServicioId")
        if "Funcionarios" in payload:
            u.Funcionarios = payload.get("Funcionarios")
        if "ReportaPMG" in payload:
            u.ReportaPMG = payload.get("ReportaPMG")
        if "IndicadorEE" in payload:
            u.IndicadorEE = payload.get("IndicadorEE")
        if "AccesoFactura" in payload:
            u.AccesoFactura = _coerce_boolish_to_int(payload.get("AccesoFactura"))

        if incoming_active is not None:
            _set_instance_active(u, incoming_active)

        if "ChkNombre" in payload and payload.get("ChkNombre") is not None:
            u.ChkNombre = int(payload.get("ChkNombre") or 1)
        elif getattr(u, "ChkNombre", None) is None:
            u.ChkNombre = 1

        if "InstitucionResponsableId" in payload:
            u.InstitucionResponsableId = payload.get("InstitucionResponsableId")
        if "ServicioResponsableId" in payload:
            u.ServicioResponsableId = payload.get("ServicioResponsableId")
        if "OrganizacionResponsable" in payload:
            u.OrganizacionResponsable = payload.get("OrganizacionResponsable")

        u.UpdatedAt = _now()
        u.ModifiedBy = self.current_user_id
        u.Version = (u.Version or 0) + 1

        self.db.commit()

    # ---------- DELETE (soft) ----------
    def delete(self, unidad_id: int) -> None:
        u = self.db.get(Unidad, unidad_id)
        if not u:
            return

        _set_instance_active(u, False)
        u.UpdatedAt = _now()
        u.ModifiedBy = self.current_user_id
        u.Version = (u.Version or 0) + 1

        self.db.commit()

    # ---------- GET detalle ----------
    def get(self, unidad_id: int) -> UnidadDTO:
        u = self.db.get(Unidad, unidad_id)
        if not u or (_ACTIVE_NAME and not getattr(u, _ACTIVE_NAME)):
            raise ValueError("Unidad no encontrada o inactiva")

        dto = _map_unidad_to_dto(u)

        # ✅ Inmuebles por SQL directo a la tabla REAL (según tu SSMS)
        inm_ids = self.list_inmuebles_ids(unidad_id)
        dto.Inmuebles = [InmuebleTopDTO(Id=i, TipoInmueble=0) for i in inm_ids]

        # Pisos/Areas desde pivotes si existieran
        UnidadPiso, UnidadArea = _lazy_models()

        if UnidadPiso is not None:
            piso_ids = [
                r.PisoId
                for r in self.db.scalars(
                    select(UnidadPiso).where(UnidadPiso.UnidadId == unidad_id)
                ).all()
            ]
            dto.Pisos = [pisoDTO(Id=int(p), NumeroPisoNombre=None, Checked=True) for p in piso_ids]

        if UnidadArea is not None:
            area_ids = [
                r.AreaId
                for r in self.db.scalars(
                    select(UnidadArea).where(UnidadArea.UnidadId == unidad_id)
                ).all()
            ]
            dto.Areas = [AreaDTO(Id=int(a), Nombre=None) for a in area_ids]

        return dto

    # ---------- LIST ----------
    def list_filter(self, f: UnidadFilterDTO, page: int, page_size: int) -> Page[UnidadListDTO]:
        q = self.db.query(Unidad)
        q = _q_filter_active(q, getattr(f, "Active", None))

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
        return Page[UnidadListDTO](
            data=data,
            meta=PageMeta(total=total, page=page, page_size=page_size, pages=pages),
        )

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

    # ============================================================
    #             NUEVAS FUNCIONES / PIVOTES (SQL REAL)
    # ============================================================

    def list_inmuebles_ids(self, unidad_id: int) -> List[int]:
        """
        ✅ Tabla real según tu SSMS: dbo.UnidadesInmuebles(UnidadId, InmuebleId)
        Donde InmuebleId = dbo.Divisiones.Id
        """
        rows = self.db.execute(
            text(
                """
                SELECT ui.InmuebleId
                FROM dbo.UnidadesInmuebles ui WITH (NOLOCK)
                WHERE ui.UnidadId = :uid
                """
            ),
            {"uid": unidad_id},
        ).all()
        return [int(r[0]) for r in rows]

    def get_with_expand(self, unidad_id: int) -> UnidadWithInmueblesDTO:
        """
        ✅ Retorna:
        - UnidadDTO base
        - InmueblesDetallados: árbol completo desde Divisiones (inmueble)
        - Además rellena Pisos/Areas (planos) derivándolos del árbol, si existen.
        """
        base = self.get(unidad_id)

        inm_ids = self.list_inmuebles_ids(unidad_id)
        base.Inmuebles = [InmuebleTopDTO(Id=i, TipoInmueble=0) for i in inm_ids]

        det: List[InmuebleDTO] = []
        isvc = InmuebleService(self.db)

        for iid in inm_ids:
            try:
                d = isvc.get(iid)
                if d:
                    det.append(d)
            except Exception:
                # no dejamos caer todo el expand por 1 inmueble malo
                continue

        # ✅ Derivar Pisos/Areas desde el árbol detallado
        piso_seen = set()
        area_seen = set()

        pisos_out: List[pisoDTO] = []
        areas_out: List[AreaDTO] = []

        for inm in det:
            for p in (getattr(inm, "Pisos", None) or []):
                pid = getattr(p, "Id", None)
                if pid and pid not in piso_seen:
                    piso_seen.add(pid)
                    pisos_out.append(
                        pisoDTO(
                            Id=int(pid),
                            NumeroPisoNombre=getattr(p, "PisoNumeroNombre", None),
                            Checked=True,
                        )
                    )

                for a in (getattr(p, "Areas", None) or []):
                    aid = getattr(a, "Id", None)
                    if aid and aid not in area_seen:
                        area_seen.add(aid)
                        areas_out.append(AreaDTO(Id=int(aid), Nombre=getattr(a, "Nombre", None)))

        # Solo setear si encontramos algo (para no “mentir” con vacíos)
        if pisos_out:
            base.Pisos = pisos_out
        if areas_out:
            base.Areas = areas_out

        return UnidadWithInmueblesDTO(**base.model_dump(), InmueblesDetallados=det)

    # (si quieres, aquí mantienes link_inmuebles_append/sync usando SQL también,
    # pero como tu foco ahora es el expand, lo dejamos fuera para no alargar)
