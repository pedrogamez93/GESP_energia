from __future__ import annotations
from typing import List, Optional, Tuple
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models.unidad import Unidad, UnidadInmueble, UnidadPiso, UnidadArea

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
    """
    Devuelve (nombre_atributo, columna) del atributo booleano de 'actividad'
    según exista en el modelo. Si no existe, (None, None).
    """
    for name in _ACTIVE_CANDIDATES:
        if hasattr(model, name):
            return name, getattr(model, name)
    return None, None

# Detectamos una vez la columna del modelo
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
        return q.filter(_ACTIVE_COL.is_(True))
    return q  # si el modelo no tiene flag de activo, no filtramos

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
            # si no hay flag, asumimos "1"
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


# ---------------------- Servicio ----------------------
class UnidadService:
    """Replica de GobEfi.Web.Services.UnidadService (lógica esencial)."""

    def __init__(self, db: Session, current_user_id: Optional[str], current_user_is_admin: bool):
        self.db = db
        self.current_user_id = current_user_id
        self.current_user_is_admin = current_user_is_admin

    # ---------- CREATE ----------
    def create(self, payload: dict) -> UnidadDTO:
        u = Unidad(
            # si existe el campo de activo, lo seteamos a True
            **({_ACTIVE_NAME: True} if _ACTIVE_NAME else {}),
            CreatedAt=_now(),
            UpdatedAt=_now(),
            CreatedBy=self.current_user_id,
            Version=1,
            Nombre=payload.get("Nombre"),
            ServicioId=payload.get("ServicioId"),
            Funcionarios=payload.get("Funcionarios"),
            ReportaPMG=payload.get("ReportaPMG") or False,
            IndicadorEE=payload.get("IndicadorEE") or False,
            AccesoFactura=payload.get("AccesoFactura"),
            InstitucionResponsableId=payload.get("InstitucionResponsableId"),
            ServicioResponsableId=payload.get("ServicioResponsableId"),
            OrganizacionResponsable=payload.get("OrganizacionResponsable"),
        )
        self.db.add(u)
        self.db.flush()  # para obtener u.Id

        inmuebles = payload.get("Inmuebles") or []
        if inmuebles:
            root = inmuebles[0]
            if root.get("Id"):
                self.db.add(UnidadInmueble(UnidadId=u.Id, InmuebleId=root["Id"]))

            for edif in (root.get("Edificios") or []):
                if edif.get("Id"):
                    self.db.add(UnidadInmueble(UnidadId=u.Id, InmuebleId=edif["Id"]))

                for piso in (edif.get("Pisos") or []):
                    if piso.get("Id"):
                        self.db.add(UnidadPiso(UnidadId=u.Id, PisoId=piso["Id"]))
                    for area in (piso.get("Areas") or []):
                        if area.get("Id"):
                            self.db.add(UnidadArea(UnidadId=u.Id, AreaId=area["Id"]))

        self.db.commit()
        self.db.refresh(u)
        return _map_unidad_to_dto(u)

    # ---------- UPDATE ----------
    def update(self, unidad_id: int, payload: dict) -> None:
        u = self.db.get(Unidad, unidad_id)
        if not u or (_ACTIVE_NAME and not getattr(u, _ACTIVE_NAME)):
            raise ValueError("Unidad no encontrada o inactiva")

        # Actualiza campos base
        u.OldId = payload.get("OldId")
        u.Nombre = payload.get("Nombre", u.Nombre)
        u.ServicioId = payload.get("ServicioId", u.ServicioId)
        u.Funcionarios = payload.get("Funcionarios", u.Funcionarios)
        if "ReportaPMG" in payload:
            u.ReportaPMG = payload.get("ReportaPMG")
        if "IndicadorEE" in payload:
            u.IndicadorEE = payload.get("IndicadorEE")
        if "AccesoFactura" in payload:
            u.AccesoFactura = payload.get("AccesoFactura")
        u.InstitucionResponsableId = payload.get("InstitucionResponsableId", getattr(u, "InstitucionResponsableId", None))
        u.ServicioResponsableId = payload.get("ServicioResponsableId", getattr(u, "ServicioResponsableId", None))
        u.OrganizacionResponsable = payload.get("OrganizacionResponsable", getattr(u, "OrganizacionResponsable", None))
        u.UpdatedAt = _now()
        u.ModifiedBy = self.current_user_id
        u.Version = (u.Version or 0) + 1

        # Limpia puentes y vuelve a crear según payload
        self.db.query(UnidadInmueble).filter_by(UnidadId=unidad_id).delete()
        self.db.query(UnidadPiso).filter_by(UnidadId=unidad_id).delete()
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
                    if piso.get("Id"):
                        self.db.add(UnidadPiso(UnidadId=unidad_id, PisoId=piso["Id"]))
                    for area in (piso.get("Areas") or []):
                        if area.get("Id"):
                            self.db.add(UnidadArea(UnidadId=unidad_id, AreaId=area["Id"]))

        self.db.commit()

    # ---------- DELETE (soft) ----------
    def delete(self, unidad_id: int) -> None:
        u = self.db.get(Unidad, unidad_id)
        if not u:
            return
        _set_instance_active(u, False)
        self.db.query(UnidadArea).filter_by(UnidadId=unidad_id).delete()
        self.db.query(UnidadPiso).filter_by(UnidadId=unidad_id).delete()
        self.db.query(UnidadInmueble).filter_by(UnidadId=unidad_id).delete()
        self.db.commit()

    # ---------- GET detalle ----------
    def get(self, unidad_id: int) -> UnidadDTO:
        u = self.db.get(Unidad, unidad_id)
        if not u or (_ACTIVE_NAME and not getattr(u, _ACTIVE_NAME)):
            raise ValueError("Unidad no encontrada o inactiva")

        dto = _map_unidad_to_dto(u)

        # Inmuebles top
        inm_ids = [
            r.InmuebleId
            for r in self.db.scalars(
                select(UnidadInmueble).where(UnidadInmueble.UnidadId == unidad_id)
            ).all()
        ]
        dto.Inmuebles = [InmuebleTopDTO(Id=i, TipoInmueble=0) for i in inm_ids]

        # Pisos
        piso_ids = [
            r.PisoId
            for r in self.db.scalars(
                select(UnidadPiso).where(UnidadPiso.UnidadId == unidad_id)
            ).all()
        ]
        dto.Pisos = [pisoDTO(Id=p, NumeroPisoNombre=None, Checked=True) for p in piso_ids]

        # Áreas
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

        # Filtro por texto (Nombre)
        if f.Unidad:
            like = f"%{f.Unidad}%"
            q = q.filter(Unidad.Nombre.ilike(like))

        # Filtro por servicio/institución (responsables)
        if f.ServicioId:
            q = q.filter(Unidad.ServicioId == f.ServicioId)
        if f.InstitucionId:
            q = q.filter(Unidad.InstitucionResponsableId == f.InstitucionId)

        # Filtro por región (raw SQL equivalente a EF .NET)
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
                q = q.filter(False)  # sin resultados

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

    # ---------- Check nombre duplicado ----------
    def check_nombre(self, nombre: str, servicio_id: int) -> bool:
        q = self.db.query(Unidad).filter(
            Unidad.Nombre == nombre,
            Unidad.ServicioId == servicio_id,
        )
        q = _q_only_actives(q)
        return bool(q.first())

    # ---------- Compatibilidad OldId ----------
    def has_inteligent_measurement(self, old_id: int) -> bool:
        found = self.db.query(Unidad).filter(Unidad.OldId == old_id).first()
        return bool(found)
