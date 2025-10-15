# app/services/division_service.py
from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.db.models.area import Area
from app.db.models.direccion import Direccion
from app.db.models.division import Division
from app.db.models.piso import Piso
from app.db.models.usuarios_divisiones import UsuarioDivision
from app.schemas.division import (
    DivisionAniosDTO,
    DivisionDTO,
    DivisionListDTO,
    DivisionPatchDTO,
    ObservacionDTO,
    ObservacionInexistenciaDTO,
    ReportaResiduosDTO,
)
from app.services.ajuste_service import AjusteService


# --------- utilidades internas ---------
def _any_key_in(keys: Iterable[str], payload_keys: Iterable[str]) -> bool:
    pl = {k.lower() for k in payload_keys}
    return any(k.lower() in pl for k in keys)


class DivisionService:
    # --------- Listado (paginado, items planos) ---------
    def list(
        self,
        db: Session,
        q: Optional[str],
        page: int,
        page_size: int,
        active: Optional[bool] = True,
        servicio_id: Optional[int] = None,
        region_id: Optional[int] = None,
        provincia_id: Optional[int] = None,
        comuna_id: Optional[int] = None,
        **_: object,
    ) -> Dict[str, Any]:
        """
        Devuelve dicts planos aplicando COALESCE con Direcciones:
        - RegionId/ProvinciaId/ComunaId/Direccion se toman de Direcciones si en Divisiones vienen NULL.
        - Filtros por Servicio/Región/Provincia/Comuna operan sobre ambos orígenes.
        - Búsqueda por Nombre/Dirección sin LOWER/UPPER (no requiere cambios de BD).
        """
        DirPref = func.coalesce(Division.Direccion, Direccion.DireccionCompleta)

        base = (
            db.query(
                Division.Id.label("Id"),
                Division.Nombre.label("Nombre"),
                Division.Active.label("Active"),
                Division.ServicioId.label("ServicioId"),
                func.coalesce(Division.RegionId, Direccion.RegionId).label("RegionId"),
                func.coalesce(Division.ProvinciaId, Direccion.ProvinciaId).label("ProvinciaId"),
                func.coalesce(Division.ComunaId, Direccion.ComunaId).label("ComunaId"),
                DirPref.label("Direccion"),
            )
            .outerjoin(Direccion, Direccion.Id == Division.DireccionInmuebleId)
        )

        # Filtros directos (aprovechan índices si existen)
        if active is not None:
            base = base.filter(Division.Active.is_(bool(active)))
        if servicio_id is not None:
            base = base.filter(Division.ServicioId == servicio_id)
        if region_id is not None:
            base = base.filter(or_(Division.RegionId == region_id, Direccion.RegionId == region_id))
        if provincia_id is not None:
            base = base.filter(or_(Division.ProvinciaId == provincia_id, Direccion.ProvinciaId == provincia_id))
        if comuna_id is not None:
            base = base.filter(or_(Division.ComunaId == comuna_id, Direccion.ComunaId == comuna_id))

        # Búsqueda: SIN LOWER()/UPPER() para no romper posibles índices.
        # En SQL Server, si tu collation es case-insensitive (lo usual), LIKE ya ignora mayúsculas.
        if q:
            like = f"%{q}%"
            base = base.filter(
                or_(
                    func.coalesce(Division.Nombre, "") .like(like),
                    func.coalesce(Division.Direccion, "") .like(like),
                    func.coalesce(Direccion.DireccionCompleta, "") .like(like),
                )
            )

        # Conteo eficiente sobre subquery de IDs (evita contar todo el join + columnas grandes)
        id_subq = base.with_entities(Division.Id).distinct().subquery()
        total = db.query(func.count()).select_from(id_subq).scalar() or 0

        # Paginación por IDs (barata) y luego fetch ordenado
        size = max(1, min(200, page_size))
        page = max(1, page)

        page_ids_rows = (
            base.with_entities(
                Division.Id.label("Id"),
                DirPref.label("OrdenDir"),
                Division.Id.label("OrdenId"),
            )
            .distinct()
            .order_by(text("OrdenDir ASC"), text("OrdenId ASC"))
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        ids = [r.Id for r in page_ids_rows] or []

        rows = []
        if ids:
            rows = (
                db.query(
                    Division.Id.label("Id"),
                    Division.Nombre.label("Nombre"),
                    Division.Active.label("Active"),
                    Division.ServicioId.label("ServicioId"),
                    func.coalesce(Division.RegionId, Direccion.RegionId).label("RegionId"),
                    func.coalesce(Division.ProvinciaId, Direccion.ProvinciaId).label("ProvinciaId"),
                    func.coalesce(Division.ComunaId, Direccion.ComunaId).label("ComunaId"),
                    DirPref.label("Direccion"),
                )
                .outerjoin(Direccion, Direccion.Id == Division.DireccionInmuebleId)
                .filter(Division.Id.in_(ids))
                .order_by(DirPref.asc(), Division.Id.asc())
                .all()
            )

        items = [
            {
                "Id": r.Id,
                "Nombre": r.Nombre,
                "Active": r.Active,
                "ServicioId": r.ServicioId,
                "RegionId": r.RegionId,
                "ProvinciaId": r.ProvinciaId,
                "ComunaId": r.ComunaId,
                "Direccion": r.Direccion,
            }
            for r in rows
        ]
        return {"total": total, "page": page, "page_size": size, "items": items}

    # --------- GET/SELECT y filtros simples ---------
    def get(self, db: Session, division_id: int) -> Division:
        obj = db.query(Division).filter(Division.Id == division_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="División no encontrada")
        return obj

    def by_user(self, db: Session, user_id: str) -> List[Division]:
        ids = db.query(UsuarioDivision.DivisionId).filter(UsuarioDivision.UsuarioId == user_id).all()
        id_list = [r[0] for r in ids]
        if not id_list:
            return []
        return db.query(Division).filter(Division.Id.in_(id_list)).order_by(Division.Direccion).all()

    def by_servicio(self, db: Session, servicio_id: int, search: Optional[str] = None) -> List[Division]:
        qy = db.query(Division).filter(Division.ServicioId == servicio_id)
        if search:
            like = f"%{search}%"
            qy = qy.filter(Division.Direccion.like(like))
        return qy.order_by(Division.Direccion).all()

    def by_edificio(self, db: Session, edificio_id: int) -> List[Division]:
        return db.query(Division).filter(Division.EdificioId == edificio_id).order_by(Division.Direccion).all()

    def by_region(self, db: Session, region_id: int) -> List[Division]:
        return db.query(Division).filter(Division.RegionId == region_id).order_by(Division.Direccion).all()

    def list_select(self, db: Session, q: Optional[str], servicio_id: int | None) -> List[tuple[int, str | None]]:
        DirPref = func.coalesce(Division.Direccion, Direccion.DireccionCompleta)
        qy = db.query(Division.Id, DirPref.label("Nombre")).outerjoin(
            Direccion, Direccion.Id == Division.DireccionInmuebleId
        )
        if servicio_id is not None:
            qy = qy.filter(Division.ServicioId == servicio_id)
        if q:
            like = f"%{q}%"
            qy = qy.filter(DirPref.like(like))
        return qy.order_by(DirPref.asc(), Division.Id.asc()).all()

    # --------- Observaciones / flags ---------
    def get_observacion_papel(self, db: Session, division_id: int) -> ObservacionDTO:
        d = self.get(db, division_id)
        return ObservacionDTO(CheckObserva=d.ObservaPapel, Observacion=d.ObservacionPapel)

    def set_observacion_papel(self, db: Session, division_id: int, payload: ObservacionDTO) -> None:
        d = self.get(db, division_id)
        d.ObservaPapel = payload.CheckObserva
        d.ObservacionPapel = payload.Observacion
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    def get_observacion_residuos(self, db: Session, division_id: int) -> ObservacionDTO:
        d = self.get(db, division_id)
        return ObservacionDTO(CheckObserva=d.ObservaResiduos, Observacion=d.ObservacionResiduos)

    def set_observacion_residuos(self, db: Session, division_id: int, payload: ObservacionDTO) -> None:
        d = self.get(db, division_id)
        d.ObservaResiduos = payload.CheckObserva
        d.ObservacionResiduos = payload.Observacion
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    def get_reporta_residuos(self, db: Session, division_id: int) -> ReportaResiduosDTO:
        d = self.get(db, division_id)
        return ReportaResiduosDTO(
            CheckReporta=d.JustificaResiduos,
            Justificacion=d.JustificacionResiduos,
            CheckReportaNoReciclados=d.JustificaResiduosNoReciclados,
            JustificacionNoReciclados=d.JustificacionResiduosNoReciclados,
        )

    def set_reporta_residuos(self, db: Session, division_id: int, payload: ReportaResiduosDTO) -> None:
        d = self.get(db, division_id)
        d.JustificaResiduos = payload.CheckReporta
        d.JustificacionResiduos = payload.Justificacion
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    def set_reporta_residuos_no_reciclados(self, db: Session, division_id: int, payload: ReportaResiduosDTO) -> None:
        d = self.get(db, division_id)
        d.JustificaResiduosNoReciclados = payload.CheckReportaNoReciclados
        d.JustificacionResiduosNoReciclados = payload.JustificacionNoReciclados
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    def get_observacion_agua(self, db: Session, division_id: int) -> ObservacionDTO:
        d = self.get(db, division_id)
        return ObservacionDTO(CheckObserva=d.ObservaAgua, Observacion=d.ObservacionAgua)

    def set_observacion_agua(self, db: Session, division_id: int, payload: ObservacionDTO) -> None:
        d = self.get(db, division_id)
        d.ObservaAgua = payload.CheckObserva
        d.ObservacionAgua = payload.Observacion
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    def get_inexistencia_eyv(self, db: Session, division_id: int) -> ObservacionInexistenciaDTO:
        d = self.get(db, division_id)
        return ObservacionInexistenciaDTO(Observacion=d.ObsInexistenciaEyV or "")

    def set_inexistencia_eyv(self, db: Session, division_id: int, payload: ObservacionInexistenciaDTO) -> None:
        d = self.get(db, division_id)
        d.ObsInexistenciaEyV = payload.Observacion
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    # --------- Reglas con Ajustes ---------
    def set_anios(self, db: Session, payload: DivisionAniosDTO, set_gestion: bool) -> None:
        aj = AjusteService(db)
        if not aj.can_edit_unidad_pmg():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Edición de Unidad PMG deshabilitada por configuración (Ajustes.EditUnidadPMG = false).",
            )
        d = self.get(db, payload.Id)
        if set_gestion:
            d.AnioInicioGestionEnergetica = payload.AnioInicioGestionEnergetica
        else:
            d.AnioInicioRestoItems = payload.AnioInicioRestoItems
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    def patch(self, db: Session, division_id: int, patch: DivisionPatchDTO) -> Division:
        """
        Aplica parches parciales. Si el payload toca campos sensibles (años/UnidadPMG),
        exige el flag de edición de Unidad PMG.
        """
        aj = AjusteService(db)
        campos_sensibles = {
            "AnioInicioGestionEnergetica",
            "AnioInicioRestoItems",
            "UnidadPMG",  # si existiera
        }
        payload = patch.model_dump(exclude_unset=True)

        if _any_key_in(campos_sensibles, payload.keys()):
            if not aj.can_edit_unidad_pmg():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Edición de Unidad PMG deshabilitada por configuración.",
                )

        d = self.get(db, division_id)
        for k, v in payload.items():
            setattr(d, k, v)

        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()
        db.refresh(d)
        return d

    # --- Soft delete en cascada ---
    def delete_soft_cascada(self, db: Session, division_id: int, user_id: str | None) -> None:
        aj = AjusteService(db)
        if not aj.can_delete_unidad_pmg():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Eliminación de Unidad PMG deshabilitada por configuración (Ajustes.DeleteUnidadPMG = false).",
            )

        d = db.query(Division.Id, Division.Active).filter(Division.Id == division_id).first()
        if not d:
            raise HTTPException(status_code=404, detail="División no encontrada")
        if not d.Active:
            return

        now = datetime.utcnow()
        try:
            with db.begin():
                piso_ids_subq = (
                    db.query(Piso.Id)
                    .filter(Piso.DivisionId == division_id, Piso.Active.is_(True))
                    .subquery()
                )

                db.query(Area).filter(
                    Area.Active.is_(True),
                    Area.PisoId.in_(select(piso_ids_subq.c.Id)),
                ).update(
                    {
                        Area.Active: False,
                        Area.UpdatedAt: now,
                        Area.ModifiedBy: user_id,
                        Area.Version: func.coalesce(Area.Version, 0) + 1,
                    },
                    synchronize_session=False,
                )

                db.query(Piso).filter(
                    Piso.DivisionId == division_id,
                    Piso.Active.is_(True),
                ).update(
                    {
                        Piso.Active: False,
                        Piso.UpdatedAt: now,
                        Piso.ModifiedBy: user_id,
                        Piso.Version: func.coalesce(Piso.Version, 0) + 1,
                    },
                    synchronize_session=False,
                )

                db.query(Division).filter(
                    Division.Id == division_id,
                    Division.Active.is_(True),
                ).update(
                    {
                        Division.Active: False,
                        Division.UpdatedAt: now,
                        Division.ModifiedBy: user_id,
                        Division.Version: func.coalesce(Division.Version, 0) + 1,
                    },
                    synchronize_session=False,
                )
        except Exception:
            db.rollback()
            raise

    # --- Activar/Desactivar en cascada ---
    def set_active_cascada(self, db: Session, division_id: int, active: bool, user_id: str | None) -> Division:
        aj = AjusteService(db)
        if not aj.can_delete_unidad_pmg():
            accion = "activar" if active else "desactivar"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes permiso para {accion} la Unidad PMG (Ajustes.DeleteUnidadPMG = false).",
            )

        d = self.get(db, division_id)
        now = datetime.utcnow()

        d.Active = bool(active)
        d.UpdatedAt = now
        d.ModifiedBy = user_id
        d.Version = (d.Version or 0) + 1

        pisos = db.query(Piso).filter(Piso.DivisionId == division_id).all()
        for p in pisos:
            p.Active = bool(active)
            p.UpdatedAt = now
            p.ModifiedBy = user_id
            p.Version = (p.Version or 0) + 1

            areas = db.query(Area).filter(Area.PisoId == p.Id).all()
            for a in areas:
                a.Active = bool(active)
                a.UpdatedAt = now
                a.ModifiedBy = user_id
                a.Version = (a.Version or 0) + 1

        db.commit()
        db.refresh(d)
        return d
