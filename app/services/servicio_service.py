from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.usuarios_servicios import UsuarioServicio
from app.db.models.servicio import Servicio
from app.schemas.servicios import (
    ServicioDTO, ServicioResponse, DiagnosticoDTO,
    ServicioCreate, ServicioUpdate
)

class ServicioService:
    def __init__(self, db: Session):
        self.db = db

    # --------- Lecturas originales ---------

    def get_by_user_id(self, user_id: str, is_admin: bool) -> ServicioResponse:
        q = self.db.query(Servicio).filter(Servicio.Active == True)
        if not is_admin:
            q = (
                q.join(UsuarioServicio, UsuarioServicio.ServicioId == Servicio.Id)
                 .filter(UsuarioServicio.UsuarioId == user_id)
            )
        servicios = q.order_by(Servicio.Nombre).all()
        return ServicioResponse(Ok=True, Servicios=[ServicioDTO.model_validate(s) for s in servicios])

    def save_justificacion(self, dto: ServicioDTO) -> None:
        srv = self.db.query(Servicio).filter(Servicio.Id == dto.Id).first()
        if not srv:
            return
        srv.Justificacion = dto.Justificacion
        if dto.RevisionRed is not None:
            srv.RevisionRed = dto.RevisionRed
        if dto.ComentarioRed is not None:
            srv.ComentarioRed = dto.ComentarioRed
        self.db.commit()

    def get_diagnostico(self, servicio_id: int) -> DiagnosticoDTO:
        srv = self.db.query(Servicio).filter(Servicio.Id == servicio_id).first()
        if not srv:
            return DiagnosticoDTO(RevisionDiagnosticoAmbiental=False, EtapaSEV=0)
        return DiagnosticoDTO(
            RevisionDiagnosticoAmbiental=srv.RevisionDiagnosticoAmbiental,
            EtapaSEV=srv.EtapaSEV
        )

    # --------- Helpers de estado (activar/desactivar) ---------

    def _set_active(self, servicio_id: int, active: bool, modified_by: str) -> Optional[Servicio]:
        srv = self.db.query(Servicio).filter(Servicio.Id == servicio_id).first()
        if not srv:
            return None

        # si no cambia el estado, sólo auditamos
        if srv.Active == active:
            srv.UpdatedAt = datetime.utcnow()
            srv.ModifiedBy = modified_by
            srv.Version = (srv.Version or 0) + 1
            self.db.commit()
            self.db.refresh(srv)
            return srv

        srv.Active = active
        srv.UpdatedAt = datetime.utcnow()
        srv.ModifiedBy = modified_by
        srv.Version = (srv.Version or 0) + 1
        self.db.commit()
        self.db.refresh(srv)
        return srv

    def deactivate(self, servicio_id: int, modified_by: str) -> Optional[Servicio]:
        return self._set_active(servicio_id, False, modified_by)

    def activate(self, servicio_id: int, modified_by: str) -> Optional[Servicio]:
        return self._set_active(servicio_id, True, modified_by)

    # --------- CRUD ADMIN ---------

    def create(self, data: ServicioCreate, created_by: str) -> Servicio:
        now = datetime.utcnow()
        srv = Servicio(
            # requeridos por DDL
            CreatedAt=now,
            UpdatedAt=now,
            Version=1,
            Active=True,

            # audit
            CreatedBy=created_by,
            ModifiedBy=created_by,

            # payload Admin Create
            Nombre=data.Nombre,
            Identificador=data.Identificador,
            ReportaPMG=data.ReportaPMG,
            InstitucionId=data.InstitucionId,
        )
        self.db.add(srv)
        self.db.commit()
        self.db.refresh(srv)
        return srv

    def update_admin(self, servicio_id: int, data: ServicioUpdate, modified_by: str) -> Optional[Servicio]:
        srv = self.db.query(Servicio).filter(Servicio.Id == servicio_id).first()
        if not srv:
            return None

        # campos editables en Admin
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(srv, field, value)

        # metacampos
        srv.UpdatedAt = datetime.utcnow()
        srv.ModifiedBy = modified_by
        srv.Version = (srv.Version or 0) + 1

        self.db.commit()
        self.db.refresh(srv)
        return srv

    def soft_delete(self, servicio_id: int, modified_by: str) -> Optional[Servicio]:
        """Paridad con .NET: baja lógica (Active = false)."""
        return self.deactivate(servicio_id, modified_by)
