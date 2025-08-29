from __future__ import annotations
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, select
from fastapi import HTTPException, status

from app.db.models.division import Division
from app.db.models.piso import Piso
from app.db.models.area import Area
from app.db.models.usuarios_divisiones import UsuarioDivision
from app.schemas.division import (
    DivisionDTO, DivisionListDTO,
    ObservacionDTO, ReportaResiduosDTO, ObservacionInexistenciaDTO,
    DivisionPatchDTO, DivisionAniosDTO
)
from app.services.ajuste_service import AjusteService 

class DivisionService:
    # --------- Listados básicos ---------
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        query = db.query(Division)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(Division.Direccion).like(func.lower(like)))
        total = query.count()
        items = (
            query.order_by(Division.Direccion)
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def get(self, db: Session, division_id: int) -> Division:
        obj = db.query(Division).filter(Division.Id == division_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="División no encontrada")
        return obj

    def by_user(self, db: Session, user_id: str) -> List[Division]:
        ids = (
            db.query(UsuarioDivision.DivisionId)
              .filter(UsuarioDivision.UsuarioId == user_id)
              .all()
        )
        id_list = [r[0] for r in ids]
        if not id_list:
            return []
        return (
            db.query(Division)
              .filter(Division.Id.in_(id_list))
              .order_by(Division.Direccion)
              .all()
        )

    def by_servicio(self, db: Session, servicio_id: int, search: Optional[str] = None) -> List[Division]:
        q = db.query(Division).filter(Division.ServicioId == servicio_id)
        if search:
            like = f"%{search}%"
            q = q.filter(func.lower(Division.Direccion).like(func.lower(like)))
        return q.order_by(Division.Direccion).all()

    def by_edificio(self, db: Session, edificio_id: int) -> List[Division]:
        return (
            db.query(Division)
              .filter(Division.EdificioId == edificio_id)
              .order_by(Division.Direccion)
              .all()
        )

    def by_region(self, db: Session, region_id: int) -> List[Division]:
        return (
            db.query(Division)
              .filter(Division.RegionId == region_id)
              .order_by(Division.Direccion)
              .all()
        )

    def list_select(self, db: Session, q: str | None, servicio_id: int | None) -> List[tuple[int, str | None]]:
        query = db.query(Division.Id, Division.Direccion)
        if servicio_id is not None:
            query = query.filter(Division.ServicioId == servicio_id)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(Division.Direccion).like(func.lower(like)))
        return query.order_by(Division.Direccion).all()

    # --------- Observaciones / flags ---------
    def get_observacion_papel(self, db: Session, division_id: int) -> ObservacionDTO:
        d = self.get(db, division_id)
        return ObservacionDTO(CheckObserva=d.ObservaPapel, Observacion=d.ObservacionPapel)

    def set_observacion_papel(self, db: Session, division_id: int, payload: ObservacionDTO):
        d = self.get(db, division_id)
        d.ObservaPapel = payload.CheckObserva
        d.ObservacionPapel = payload.Observacion
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    def get_observacion_residuos(self, db: Session, division_id: int) -> ObservacionDTO:
        d = self.get(db, division_id)
        return ObservacionDTO(CheckObserva=d.ObservaResiduos, Observacion=d.ObservacionResiduos)

    def set_observacion_residuos(self, db: Session, division_id: int, payload: ObservacionDTO):
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
            JustificacionNoReciclados=d.JustificacionResiduosNoReciclados
        )

    def set_reporta_residuos(self, db: Session, division_id: int, payload: ReportaResiduosDTO):
        d = self.get(db, division_id)
        d.JustificaResiduos = payload.CheckReporta
        d.JustificacionResiduos = payload.Justificacion
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    def set_reporta_residuos_no_reciclados(self, db: Session, division_id: int, payload: ReportaResiduosDTO):
        d = self.get(db, division_id)
        d.JustificaResiduosNoReciclados = payload.CheckReportaNoReciclados
        d.JustificacionResiduosNoReciclados = payload.JustificacionNoReciclados
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    def get_observacion_agua(self, db: Session, division_id: int) -> ObservacionDTO:
        d = self.get(db, division_id)
        return ObservacionDTO(CheckObserva=d.ObservaAgua, Observacion=d.ObservacionAgua)

    def set_observacion_agua(self, db: Session, division_id: int, payload: ObservacionDTO):
        d = self.get(db, division_id)
        d.ObservaAgua = payload.CheckObserva
        d.ObservacionAgua = payload.Observacion
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    def get_inexistencia_eyv(self, db: Session, division_id: int) -> ObservacionInexistenciaDTO:
        d = self.get(db, division_id)
        return ObservacionInexistenciaDTO(Observacion=d.ObsInexistenciaEyV or "")

    def set_inexistencia_eyv(self, db: Session, division_id: int, payload: ObservacionInexistenciaDTO):
        d = self.get(db, division_id)
        d.ObsInexistenciaEyV = payload.Observacion
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    # --------- Reglas con Ajustes ---------
    def set_anios(self, db: Session, payload: DivisionAniosDTO, set_gestion: bool):
        aj = AjusteService(db)
        if not aj.can_edit_unidad_pmg():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Edición de Unidad PMG deshabilitada por configuración (Ajustes.EditUnidadPMG = false)."
            )
        d = self.get(db, payload.Id)
        if set_gestion:
            d.AnioInicioGestionEnergetica = payload.AnioInicioGestionEnergetica
        else:
            d.AnioInicioRestoItems = payload.AnioInicioRestoItems
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()

    def patch(self, db: Session, division_id: int, patch: DivisionPatchDTO):
        aj = AjusteService(db)
        # Muchos paneles de PMG editan estos campos: se respeta el switch global
        if not aj.can_edit_unidad_pmg():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Edición de Unidad PMG deshabilitada por configuración."
            )
        d = self.get(db, division_id)
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(d, k, v)
        d.UpdatedAt = datetime.utcnow()
        d.Version = (d.Version or 0) + 1
        db.commit()
        db.refresh(d)
        return d

def delete_soft_cascada(self, db: Session, division_id: int, user_id: str | None):
    aj = AjusteService(db)
    if not aj.can_delete_unidad_pmg():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Eliminación de Unidad PMG deshabilitada por configuración (Ajustes.DeleteUnidadPMG = false)."
        )

    # Verifica existencia y estado actual sin cargar toda la entidad
    d = db.query(Division.Id, Division.Active).filter(Division.Id == division_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="División no encontrada")
    if not d.Active:
        # Ya estaba inactiva; no hacemos nada (idempotente)
        return

    now = datetime.utcnow()

    try:
        # Una sola transacción para todo
        with db.begin():
            # --- ÁREAS ---
            # Subconsulta de pisos activos de la división
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

            # --- PISOS ---
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

            # --- DIVISIÓN ---
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
        # with db.begin() hace commit automático si no hay excepciones
    except Exception:
        # Por si el contexto ya hizo rollback, volvemos a elevar
        db.rollback()
        raise
    
# --- NUEVO: activar/desactivar en cascada ---
def set_active_cascada(self, db: Session, division_id: int, active: bool, user_id: str | None):
    aj = AjusteService(db)
    # Usamos la misma guarda que el delete "blando" (ajústala si quieres otra política)
    if not aj.can_delete_unidad_pmg():
        from fastapi import HTTPException, status
        accion = "activar" if active else "desactivar"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No tienes permiso para {accion} la Unidad PMG (Ajustes.DeleteUnidadPMG = false)."
        )

    d = self.get(db, division_id)
    now = datetime.utcnow()

    # Set estado división
    d.Active = bool(active)
    d.UpdatedAt = now
    d.ModifiedBy = user_id
    d.Version = (d.Version or 0) + 1

    # Cascada a Pisos y Áreas
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