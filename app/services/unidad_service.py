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
    UnidadDivisionDTO,
)
from app.schemas.inmuebles import InmuebleDTO
from app.schemas.pagination import Page, PageMeta

from app.services.inmueble_service import InmuebleService


# ---------------------- Helpers ----------------------
_ACTIVE_CANDIDATES = ("Active", "Activo", "IsActive", "Enabled")

def _sql_pisos_origen() -> str:
    return """
    DECLARE @uid INT = :uid;

    ;WITH pisos AS (
        -- A) Pisos directos
        SELECT DISTINCT
            p.Id        AS PisoId,
            p.DivisionId,
            'pisos'     AS origen,
            1           AS prio
        FROM dbo.UnidadesPisos up
        JOIN dbo.Pisos p ON p.Id = up.PisoId
        WHERE up.UnidadId = @uid

        UNION ALL

        -- B) Pisos indirectos por áreas
        SELECT DISTINCT
            p.Id        AS PisoId,
            p.DivisionId,
            'areas'     AS origen,
            2           AS prio
        FROM dbo.UnidadesAreas ua
        JOIN dbo.Areas a ON a.Id = ua.AreaId
        JOIN dbo.Pisos p ON p.Id = a.PisoId
        WHERE ua.UnidadId = @uid
    )
    SELECT PisoId, DivisionId, origen, prio
    FROM pisos
    """

def _sql_division_principal() -> str:
    return """
    DECLARE @uid INT = :uid;

    ;WITH divs AS (
      SELECT DISTINCT p.DivisionId, 'pisos' AS origen, 1 AS prio
      FROM dbo.UnidadesPisos up
      JOIN dbo.Pisos p ON p.Id = up.PisoId
      WHERE up.UnidadId = @uid AND p.DivisionId IS NOT NULL

      UNION ALL

      SELECT DISTINCT p.DivisionId, 'areas' AS origen, 2 AS prio
      FROM dbo.UnidadesAreas ua
      JOIN dbo.Areas a ON a.Id = ua.AreaId
      JOIN dbo.Pisos p ON p.Id = a.PisoId
      WHERE ua.UnidadId = @uid AND p.DivisionId IS NOT NULL
    )
    SELECT TOP 1 DivisionId, origen
    FROM divs
    ORDER BY prio
    """

def _coerce_boolish_to_bool(v) -> Optional[bool]:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"1", "si", "sí", "true", "t", "y", "yes"}:
        return True
    if s in {"0", "no", "false", "f", "n"}:
        return False
    # fallback: intenta int
    try:
        return bool(int(s))
    except Exception:
        return None
    
def _sql_areas_by_unidad() -> str:
    return """
    DECLARE @uid INT = :uid;

    ;WITH pisos AS (
        SELECT DISTINCT p.Id AS PisoId
        FROM dbo.UnidadesPisos up
        JOIN dbo.Pisos p ON p.Id = up.PisoId
        WHERE up.UnidadId = @uid

        UNION

        SELECT DISTINCT a.PisoId
        FROM dbo.UnidadesAreas ua
        JOIN dbo.Areas a ON a.Id = ua.AreaId
        WHERE ua.UnidadId = @uid
    )
    SELECT DISTINCT
        a.Id     AS AreaId,
        a.Nombre AS AreaNombre,
        a.PisoId
    FROM dbo.Areas a
    JOIN pisos px ON px.PisoId = a.PisoId
    WHERE EXISTS (
        SELECT 1
        FROM dbo.UnidadesAreas ua
        WHERE ua.UnidadId = @uid AND ua.AreaId = a.Id
    )
    """

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

            # ✅ nuevos
            "TipoUsoId": getattr(u, "TipoUsoId", None),
            "SuperficieM2": float(getattr(u, "SuperficieM2", None)) if getattr(u, "SuperficieM2", None) is not None else None,
            "TipoPropiedadId": getattr(u, "TipoPropiedadId", None),
            "NumeroRol": getattr(u, "NumeroRol", None),
            "NoPoseeRol": bool(getattr(u, "NoPoseeRol", False)),
            "AnioConstruccion": getattr(u, "AnioConstruccion", None),
            "OtrosColaboradores": getattr(u, "OtrosColaboradores", None),

            "AccesoFacturaAgua": bool(getattr(u, "AccesoFacturaAgua", False)),

            "ConsumeElectricidad": bool(getattr(u, "ConsumeElectricidad", False)),
            "ComparteMedidorElectricidad": bool(getattr(u, "ComparteMedidorElectricidad", False)),
            "ConsumeGas": bool(getattr(u, "ConsumeGas", False)),
            "ComparteMedidorGas": bool(getattr(u, "ComparteMedidorGas", False)),
            "ConsumeAgua": bool(getattr(u, "ConsumeAgua", False)),
            "ComparteMedidorAgua": bool(getattr(u, "ComparteMedidorAgua", False)),

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

            # ✅ nuevos
            "TipoUsoId": getattr(u, "TipoUsoId", None),
            "SuperficieM2": float(getattr(u, "SuperficieM2", None)) if getattr(u, "SuperficieM2", None) is not None else None,
            "TipoPropiedadId": getattr(u, "TipoPropiedadId", None),
            "NumeroRol": getattr(u, "NumeroRol", None),
            "NoPoseeRol": bool(getattr(u, "NoPoseeRol", False)),
            "AnioConstruccion": getattr(u, "AnioConstruccion", None),
            "OtrosColaboradores": getattr(u, "OtrosColaboradores", None),

            "AccesoFacturaAgua": bool(getattr(u, "AccesoFacturaAgua", False)),

            "ConsumeElectricidad": bool(getattr(u, "ConsumeElectricidad", False)),
            "ComparteMedidorElectricidad": bool(getattr(u, "ComparteMedidorElectricidad", False)),
            "ConsumeGas": bool(getattr(u, "ConsumeGas", False)),
            "ComparteMedidorGas": bool(getattr(u, "ComparteMedidorGas", False)),
            "ConsumeAgua": bool(getattr(u, "ConsumeAgua", False)),
            "ComparteMedidorAgua": bool(getattr(u, "ComparteMedidorAgua", False)),
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
                # ✅ nuevos
                TipoUsoId=payload.get("TipoUsoId"),
                SuperficieM2=payload.get("SuperficieM2"),
                TipoPropiedadId=payload.get("TipoPropiedadId"),
                NumeroRol=payload.get("NumeroRol"),
                NoPoseeRol=_coerce_boolish_to_bool(payload.get("NoPoseeRol")) or False,
                AnioConstruccion=payload.get("AnioConstruccion"),
                OtrosColaboradores=payload.get("OtrosColaboradores"),
                AccesoFacturaAgua=_coerce_boolish_to_bool(payload.get("AccesoFacturaAgua")) or False,

                ConsumeElectricidad=_coerce_boolish_to_bool(payload.get("ConsumeElectricidad")) or False,
                ComparteMedidorElectricidad=_coerce_boolish_to_bool(payload.get("ComparteMedidorElectricidad")) or False,
                ConsumeGas=_coerce_boolish_to_bool(payload.get("ConsumeGas")) or False,
                ComparteMedidorGas=_coerce_boolish_to_bool(payload.get("ComparteMedidorGas")) or False,
                ConsumeAgua=_coerce_boolish_to_bool(payload.get("ConsumeAgua")) or False,
                ComparteMedidorAgua=_coerce_boolish_to_bool(payload.get("ComparteMedidorAgua")) or False,
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

        if "TipoUsoId" in payload:
            u.TipoUsoId = payload.get("TipoUsoId")
        if "SuperficieM2" in payload:
            u.SuperficieM2 = payload.get("SuperficieM2")
        if "TipoPropiedadId" in payload:
            u.TipoPropiedadId = payload.get("TipoPropiedadId")

        if "NumeroRol" in payload:
            u.NumeroRol = payload.get("NumeroRol")

        if "NoPoseeRol" in payload:
            b = _coerce_boolish_to_bool(payload.get("NoPoseeRol"))
            if b is not None:
                u.NoPoseeRol = b

        if "AnioConstruccion" in payload:
            u.AnioConstruccion = payload.get("AnioConstruccion")
        if "OtrosColaboradores" in payload:
            u.OtrosColaboradores = payload.get("OtrosColaboradores")

        if "AccesoFacturaAgua" in payload:
            b = _coerce_boolish_to_bool(payload.get("AccesoFacturaAgua"))
            if b is not None:
                u.AccesoFacturaAgua = b

        for k in [
            "ConsumeElectricidad",
            "ComparteMedidorElectricidad",
            "ConsumeGas",
            "ComparteMedidorGas",
            "ConsumeAgua",
            "ComparteMedidorAgua",
        ]:
            if k in payload:
                b = _coerce_boolish_to_bool(payload.get(k))
                if b is not None:
                    setattr(u, k, b)

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
        ✅ Expand REAL:
        - Unidad base
        - Division principal (DivisionId + origen)
        - Pisos (directos o por áreas), con origen/prio/división
        - Áreas ligadas a la unidad (con PisoId)
        - InmueblesDetallados (si existen vínculos)
        """
        base = self.get(unidad_id)  # mantiene tu validación Active + mapping

        # 1) Inmuebles IDs (si aplica)
        inm_ids = self.list_inmuebles_ids(unidad_id)
        base.Inmuebles = [InmuebleTopDTO(Id=i, TipoInmueble=0) for i in inm_ids]

        # 2) Division principal
        div_row = self.db.execute(text(_sql_division_principal()), {"uid": unidad_id}).first()
        division = None
        if div_row:
            division = UnidadDivisionDTO(Id=int(div_row[0]), Origen=str(div_row[1]))
        # NOTA: si no hay división, queda None

        # 3) Pisos con origen/prio/división (incluye indirectos por áreas)
        piso_rows = self.db.execute(text(_sql_pisos_origen()), {"uid": unidad_id}).all()

        # Armamos dict por PisoId
        pisos_map: dict[int, pisoDTO] = {}
        for r in piso_rows:
            pid = int(r[0])
            div_id = int(r[1]) if r[1] is not None else None
            origen = str(r[2]) if r[2] is not None else None
            prio = int(r[3]) if r[3] is not None else None

            # si viene repetido, nos quedamos con el de menor prio (pisos=1 gana)
            if pid in pisos_map and pisos_map[pid].Prio is not None and prio is not None:
                if prio >= (pisos_map[pid].Prio or 999):
                    continue

            pisos_map[pid] = pisoDTO(
                Id=pid,
                NumeroPisoNombre=None,  # si quieres, luego lo consultamos desde dbo.Pisos
                Checked=True,
                DivisionId=div_id,
                Origen=origen,
                Prio=prio,
                Areas=[],
            )

        # 4) Áreas ligadas a la unidad (con PisoId) y asignarlas al piso
        area_rows = self.db.execute(text(_sql_areas_by_unidad()), {"uid": unidad_id}).all()

        for r in area_rows:
            aid = int(r[0])         # AreaId
            aname = r[1]            # AreaNombre
            piso_id = int(r[2]) if r[2] is not None else None

            a_dto = AreaDTO(Id=aid, Nombre=aname, PisoId=piso_id)

            # asegura que el piso exista en el mapa (aunque viniera solo por áreas)
            if piso_id is not None and piso_id not in pisos_map:
                pisos_map[piso_id] = pisoDTO(
                    Id=piso_id,
                    NumeroPisoNombre=None,
                    Checked=True,
                    DivisionId=None,
                    Origen="areas",
                    Prio=2,
                    Areas=[],
                )

            if piso_id is not None:
                pisos_map[piso_id].Areas.append(a_dto)

        # 5) Ordenar pisos por prio y por Id (estable)
        pisos_out = sorted(
            pisos_map.values(),
            key=lambda x: ((x.Prio or 99), x.Id),
        )

        # 6) (Opcional) Detalle de inmuebles
        det: List[InmuebleDTO] = []
        if inm_ids:
            isvc = InmuebleService(self.db)
            for iid in inm_ids:
                try:
                    d = isvc.get(iid)
                    if d:
                        det.append(d)
                except Exception:
                    continue

        # 7) Setear en base (sin “mentir” con vacíos)
        base.Pisos = pisos_out
        base.Areas = [a for p in pisos_out for a in (p.Areas or [])]  # plano, opcional

        # 8) Devolver DTO expand
        return UnidadWithInmueblesDTO(
            **base.model_dump(),
            InmueblesDetallados=det,
            Division=division,
        )

