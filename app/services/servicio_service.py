# app/services/servicio_service.py
from datetime import datetime
from typing import Optional, Literal, Dict, List

from sqlalchemy.orm import Session

from app.db.models.usuarios_servicios import UsuarioServicio
from app.db.models.servicio import Servicio
from app.db.models.institucion import Institucion

from app.schemas.servicios import (
    ServicioDTO,
    ServicioResponse,
    DiagnosticoDTO,
    ServicioCreate,
    ServicioUpdate,
    # 👇 NUEVOS (los agregas en app/schemas/servicios.py)
    InstitucionServiciosDTO,
    ServicioListDTO,
)

ServicioEstadoFiltro = Literal["all", "active", "inactive"]


class ServicioService:
    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------------------
    # NUEVO: Instituciones con sus servicios (activos/inactivos)
    # ---------------------------------------------------------------------
    def list_instituciones_con_servicios(
        self,
        institucion_id: Optional[int] = None,
        estado: ServicioEstadoFiltro = "all",
    ) -> List[InstitucionServiciosDTO]:
        """
        Devuelve instituciones con su lista de servicios.

        Reglas:
        - Por defecto (estado="all"): incluye servicios activos e inactivos.
        - estado="active": solo servicios Active=True.
        - estado="inactive": solo servicios Active=False.
        - Si institucion_id viene: filtra a una sola institución.

        Nota:
        - Usa JOIN => solo instituciones que tengan al menos 1 servicio.
          (Si quieres incluir instituciones sin servicios, lo cambiamos a outerjoin)
        """

        q = (
            self.db.query(
                Institucion.Id,
                Institucion.Nombre,
                Institucion.Active,
                Servicio.Id,
                Servicio.Nombre,
                Servicio.Active,
            )
            .join(Servicio, Servicio.InstitucionId == Institucion.Id)
        )

        if institucion_id is not None:
            q = q.filter(Institucion.Id == institucion_id)

        if estado == "active":
            q = q.filter(Servicio.Active == True)   # noqa: E712
        elif estado == "inactive":
            q = q.filter(Servicio.Active == False)  # noqa: E712
        else:
            # "all": no filtra por estado
            pass

        rows = q.order_by(Institucion.Nombre, Servicio.Nombre).all()

        # Agrupar en memoria: { institucion_id: InstitucionServiciosDTO(...) }
        out: Dict[int, InstitucionServiciosDTO] = {}

        for inst_id, inst_nombre, inst_active, srv_id, srv_nombre, srv_active in rows:
            if inst_id not in out:
                out[inst_id] = InstitucionServiciosDTO(
                    Id=inst_id,
                    Nombre=inst_nombre,
                    Active=inst_active,
                    Servicios=[],
                )

            out[inst_id].Servicios.append(
                ServicioListDTO(
                    Id=srv_id,
                    Nombre=srv_nombre,
                    Active=srv_active,
                )
            )

        return list(out.values())

    # --------- Lecturas originales ---------

    def get_by_user_id(self, user_id: str, is_admin: bool) -> ServicioResponse:
        q = self.db.query(Servicio).filter(Servicio.Active == True)  # noqa: E712
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
