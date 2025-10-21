from __future__ import annotations
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models.unidad import Unidad, UnidadInmueble, UnidadPiso, UnidadArea

# ⬇️ Solo DTOs de unidad que realmente usamos aquí
from app.schemas.unidad import (
    UnidadDTO,
    UnidadListDTO,
    UnidadFilterDTO,
    InmuebleTopDTO,
    pisoDTO,
    AreaDTO,
)

# ⬇️ Paginación centralizada (Pydantic v2)
from app.schemas.pagination import Page, PageMeta


# ---------------------- Helpers ----------------------
def _now() -> datetime:
    return datetime.now()


def _map_unidad_to_dto(u: Unidad) -> UnidadDTO:
    # Inmuebles/Pisos/Areas se proyectan en llamadas específicas
    return UnidadDTO.model_validate(
        {
            "Id": u.Id,
            "OldId": u.OldId,
            "Nombre": u.Nombre,
            "ServicioId": u.ServicioId or 0,
            "ServicioNombre": None,
            "InstitucionNombre": None,
            "Active": "1" if u.Active else "0",
            "Funcionarios": u.Funcionarios or 0,
            "ReportaPMG": bool(u.ReportaPMG),
            "IndicadorEE": bool(u.IndicadorEE),
            "AccesoFactura": u.AccesoFactura or 0,
            "InstitucionResponsableId": u.InstitucionResponsableId,
            "ServicioResponsableId": u.ServicioResponsableId,
            "OrganizacionResponsable": u.OrganizacionResponsable,
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
    return UnidadListDTO.model_validate(
        {
            "Id": u.Id,
            "OldId": u.OldId,
            "Nombre": u.Nombre,
            "Ubicacion": None,
            "InstitucionId": u.InstitucionResponsableId or 0,
            "InstitucionNombre": institucion_nombre or "",
            "ServicioId": u.ServicioId or 0,
            "ServicioNombre": servicio_nombre or "",
            "Active": "1" if u.Active else "0",
            "Funcionarios": u.Funcionarios or 0,
            "ReportaPMG": bool(u.ReportaPMG),
            "IndicadorEE": bool(u.IndicadorEE),
            "AccesoFactura": "1" if (u.AccesoFactura or 0) > 0 else "0",
            "InstitucionResponsableId": u.InstitucionResponsableId,
            "InstitucionResponsableNombre": institucion_nombre,
            "ServicioResponsableId": u.ServicioResponsableId,
            "ServicioResponsableNombre": servicio_nombre,
            "OrganizacionResponsable": u.OrganizacionResponsable,
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
        """
        payload esperado (acorde a .NET):
        - Campos de Unidad (Nombre, ServicioId, Funcionarios, ReportaPMG, IndicadorEE, AccesoFactura,
          InstitucionResponsableId, ServicioResponsableId, OrganizacionResponsable, ...)
        - Inmuebles: [ { Id, Edificios: [ { Id, Pisos: [ { Id, Areas: [ { Id } ] } ] } ] } ]
          * Se utiliza Inmuebles[0] como raíz; de ahí se agregan puentes a Inmueble/Pisos/Areas
        """
        u = Unidad(
            Active=True,
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
        if not u or not u.Active:
            raise ValueError("Unidad no encontrada o inactiva")

        # Actualiza campos base
        u.OldId = payload.get("OldId")
        u.Nombre = payload.get("Nombre", u.Nombre)
        u.ServicioId = payload.get("ServicioId", u.ServicioId)
        u.Funcionarios = payload.get("Funcionarios", u.Funcionarios)
        u.ReportaPMG = payload.get("ReportaPMG", u.ReportaPMG)
        u.IndicadorEE = payload.get("IndicadorEE", u.IndicadorEE)
        u.AccesoFactura = payload.get("AccesoFactura", u.AccesoFactura)
        u.InstitucionResponsableId = payload.get("InstitucionResponsableId", u.InstitucionResponsableId)
        u.ServicioResponsableId = payload.get("ServicioResponsableId", u.ServicioResponsableId)
        u.OrganizacionResponsable = payload.get("OrganizacionResponsable", u.OrganizacionResponsable)
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
        u.Active = False
        self.db.query(UnidadArea).filter_by(UnidadId=unidad_id).delete()
        self.db.query(UnidadPiso).filter_by(UnidadId=unidad_id).delete()
        self.db.query(UnidadInmueble).filter_by(UnidadId=unidad_id).delete()
        self.db.commit()

    # ---------- GET detalle ----------
    def get(self, unidad_id: int) -> UnidadDTO:
        u = self.db.get(Unidad, unidad_id)
        if not u or not u.Active:
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
        # ⚠️ Campo 'Nombre' (no 'Nomnbre')
        dto.Areas = [AreaDTO(Id=a, Nombre=None) for a in area_ids]

        return dto

    # ---------- LIST (filter + pagination) ----------
    def list_filter(self, f: UnidadFilterDTO, page: int, page_size: int) -> Page[UnidadListDTO]:
        q = self.db.query(Unidad).filter(Unidad.Active.is_(True))

        # Filtro por texto (Nombre)
        if f.Unidad:
            like = f"%{f.Unidad}%"
            q = q.filter(Unidad.Nombre.ilike(like))

        # Filtro por servicio/institución (responsables)
        if f.ServicioId:
            q = q.filter(Unidad.ServicioId == f.ServicioId)
        if f.InstitucionId:
            q = q.filter(Unidad.InstitucionResponsableId == f.InstitucionId)

        # Filtro por región (vía JOINs raw equivalentes a EF de .NET)
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
                q = q.filter(False)  # devuelve vacío

        total: int = q.count()
        items: List[Unidad] = (
            q.order_by(Unidad.Nombre).offset((page - 1) * page_size).limit(page_size).all()
        )

        data = [_map_unidad_to_listdto(u) for u in items]
        pages = (total + page_size - 1) // page_size
        return Page[UnidadListDTO](data=data, meta=PageMeta(total=total, page=page, page_size=page_size, pages=pages))

    # ---------- Asociados por usuario ----------
    def list_asociados_by_user(self, user_id: str) -> List[UnidadListDTO]:
        q = self.db.query(Unidad).filter(Unidad.Active.is_(True))
        if not self.current_user_is_admin:
            # Espera tabla UsuarioUnidades (ajusta si difiere)
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

        items = q.order_by(Unidad.Nombre).all()
        return [_map_unidad_to_listdto(u) for u in items]

    # ---------- Check nombre duplicado ----------
    def check_nombre(self, nombre: str, servicio_id: int) -> bool:
        exists = (
            self.db.query(Unidad)
            .filter(
                Unidad.Active.is_(True),
                Unidad.Nombre == nombre,
                Unidad.ServicioId == servicio_id,
            )
            .first()
        )
        return bool(exists)

    # ---------- Compatibilidad OldId ----------
    def has_inteligent_measurement(self, old_id: int) -> bool:
        found = self.db.query(Unidad).filter(Unidad.OldId == old_id).first()
        return bool(found)
