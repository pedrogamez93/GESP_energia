# app/services/inmueble_service.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.models.division import Division
from app.db.models.direccion import Direccion
from app.db.models.unidad_inmueble import UnidadInmueble
from app.schemas.inmuebles import (
    InmuebleDTO, InmuebleListDTO,
    InmuebleCreate, InmuebleUpdate,
    DireccionDTO, InmuebleByAddressRequest
)

class InmuebleService:
    def __init__(self, db: Session):
        self.db = db

    # -------- Helpers --------
    def _to_list_dto(self, d: Division, dir_: Direccion | None) -> InmuebleListDTO:
        dirdto = DireccionDTO.model_validate(dir_) if dir_ else None
        return InmuebleListDTO(
            Id=d.Id, Nombre=d.Nombre, TipoInmueble=d.TipoInmueble,
            ParentId=d.ParentId, ServicioId=d.ServicioId, Active=d.Active,
            RegionId=d.RegionId, ComunaId=d.ComunaId, Direccion=dirdto
        )

    def _to_detail_dto(self, d: Division, dir_: Direccion | None) -> InmuebleDTO:
        base = self._to_list_dto(d, dir_)
        return InmuebleDTO(
            **base.model_dump(),
            AnyoConstruccion=d.AnyoConstruccion,
            Superficie=d.Superficie,
            NroRol=d.NroRol,
            GeVersion=d.GeVersion,
        )

    # -------- Listado/filtrado (paginado) --------
    def list_paged(
        self,
        page: int = 1,
        page_size: int = 50,
        active: Optional[bool] = True,
        servicio_id: Optional[int] = None,
        region_id: Optional[int] = None,
        comuna_id: Optional[int] = None,
        tipo_inmueble: Optional[int] = None,
        search: Optional[str] = None,
        gev: Optional[int] = None,  # equivalente a GeVersion==3 (GEV3 en .NET v2)
    ) -> Tuple[int, List[InmuebleListDTO]]:
        q = self.db.query(Division).filter(Division.Active == (active if active is not None else Division.Active))
        if servicio_id is not None:
            q = q.filter(Division.ServicioId == servicio_id)
        if region_id is not None:
            q = q.filter(Division.RegionId == region_id)
        if comuna_id is not None:
            q = q.filter(Division.ComunaId == comuna_id)
        if tipo_inmueble is not None:
            q = q.filter(Division.TipoInmueble == tipo_inmueble)
        if gev is not None:
            q = q.filter(Division.GeVersion == gev)
        if search:
            like = f"%{search}%"
            q = q.filter(or_(Division.Nombre.like(like), Division.Direccion.like(like), Division.NroRol.like(like)))

        total = q.count()
        size = max(1, min(200, page_size))
        items = (
            q.order_by(Division.Nombre)
             .offset((page - 1) * size)
             .limit(size)
             .all()
        )

        # trae direcciones en bloque
        dir_map = {}
        dir_ids = [i.DireccionInmuebleId for i in items if i.DireccionInmuebleId]
        if dir_ids:
            for d in self.db.query(Direccion).filter(Direccion.Id.in_(dir_ids)).all():
                dir_map[d.Id] = d

        dto_items = [self._to_list_dto(i, dir_map.get(i.DireccionInmuebleId)) for i in items]
        return total, dto_items

    # -------- Detalle --------
    def get(self, inmueble_id: int) -> InmuebleDTO | None:
        d = self.db.query(Division).filter(Division.Id == inmueble_id, Division.Active == True).first()
        if not d:
            return None
        dir_ = None
        if d.DireccionInmuebleId:
            dir_ = self.db.query(Direccion).filter(Direccion.Id == d.DireccionInmuebleId).first()
        return self._to_detail_dto(d, dir_)

    # -------- Crear / Actualizar --------
    def _ensure_direccion(self, payload: DireccionDTO | None, parent: Division | None) -> int | None:
        if payload is None and parent is None:
            return None
        if payload is None and parent is not None and parent.DireccionInmuebleId:
            return parent.DireccionInmuebleId  # hereda del padre (como en .NET)
        if payload:
            dir_ = Direccion(
                Calle=payload.Calle,
                Numero=payload.Numero,
                RegionId=payload.RegionId or 0,
                ProvinciaId=payload.ProvinciaId or 0,
                ComunaId=payload.ComunaId or 0,
                DireccionCompleta=payload.DireccionCompleta,
            )
            self.db.add(dir_)
            self.db.flush()
            return dir_.Id
        return None

    def create(self, data: InmuebleCreate, created_by: str) -> InmuebleDTO:
        parent = None
        if data.ParentId:
            parent = self.db.query(Division).filter(Division.Id == data.ParentId).first()
        dir_id = self._ensure_direccion(data.Direccion, parent)

        now = datetime.utcnow()
        obj = Division(
            CreatedAt=now, UpdatedAt=now, Version=1, Active=True,
            CreatedBy=created_by, ModifiedBy=created_by,
            # payload
            TipoInmueble=data.TipoInmueble,
            Nombre=data.Nombre,
            AnyoConstruccion=data.AnyoConstruccion,
            ServicioId=data.ServicioId,
            TipoPropiedadId=data.TipoPropiedadId,
            EdificioId=data.EdificioId,
            Superficie=data.Superficie,
            TipoUsoId=data.TipoUsoId,
            TipoAdministracionId=data.TipoAdministracionId,
            AdministracionServicioId=data.AdministracionServicioId,
            ParentId=data.ParentId,
            NroRol=data.NroRol,
            DireccionInmuebleId=dir_id
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        dir_ = self.db.query(Direccion).filter(Direccion.Id == obj.DireccionInmuebleId).first() if obj.DireccionInmuebleId else None
        return self._to_detail_dto(obj, dir_)

    def update(self, inmueble_id: int, data: InmuebleUpdate, modified_by: str) -> InmuebleDTO | None:
        obj = self.db.query(Division).filter(Division.Id == inmueble_id).first()
        if not obj:
            return None

        # dirección
        parent = None
        if data.ParentId:
            parent = self.db.query(Division).filter(Division.Id == data.ParentId).first()
        if data.Direccion is not None:
            if obj.DireccionInmuebleId:
                dir_ = self.db.query(Direccion).filter(Direccion.Id == obj.DireccionInmuebleId).first()
                if dir_:
                    for k, v in data.Direccion.model_dump(exclude_unset=True).items():
                        setattr(dir_, k, v)
            else:
                obj.DireccionInmuebleId = self._ensure_direccion(data.Direccion, parent)

        # resto de campos
        for k, v in data.model_dump(exclude_unset=True, exclude={"Direccion"}).items():
            setattr(obj, k, v)

        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        obj.Version = (obj.Version or 0) + 1

        self.db.commit()
        self.db.refresh(obj)
        dir_ = self.db.query(Direccion).filter(Direccion.Id == obj.DireccionInmuebleId).first() if obj.DireccionInmuebleId else None
        return self._to_detail_dto(obj, dir_)

    # -------- Borrado (soft) --------
    def soft_delete(self, inmueble_id: int, modified_by: str) -> InmuebleDTO | None:
        obj = self.db.query(Division).filter(Division.Id == inmueble_id).first()
        if not obj:
            return None
        if not obj.Active:
            return self.get(inmueble_id)

        obj.Active = False
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        obj.Version = (obj.Version or 0) + 1

        # compat: si es “inmueble” contenedor (TipoInmueble == 1), apaga hijos (Divisiones con ParentId = Id)
        if obj.TipoInmueble == 1:
            self.db.query(Division).filter(Division.ParentId == inmueble_id, Division.Active == True)\
                .update({Division.Active: False}, synchronize_session=False)

        self.db.commit()
        return self.get(inmueble_id)

    # -------- Búsqueda por dirección (como .NET) --------
    def get_by_address(self, req: InmuebleByAddressRequest) -> List[InmuebleListDTO]:
        dir_ = self.db.query(Direccion)\
            .filter(Direccion.Calle == req.Calle, Direccion.Numero == req.Numero, Direccion.ComunaId == req.ComunaId)\
            .first()
        if not dir_:
            return []
        inmuebles = self.db.query(Division).filter(Division.DireccionInmuebleId == dir_.Id, Division.Active == True).all()
        return [self._to_list_dto(i, dir_) for i in inmuebles]

    # -------- Vínculos con Unidades (Add/Remove) --------
    def add_unidad(self, inmueble_id: int, unidad_id: int) -> None:
        exists = self.db.query(UnidadInmueble)\
            .filter(UnidadInmueble.InmuebleId == inmueble_id, UnidadInmueble.UnidadId == unidad_id)\
            .first()
        if exists:
            return
        link = UnidadInmueble(InmuebleId=inmueble_id, UnidadId=unidad_id)
        self.db.add(link)
        self.db.commit()

    def remove_unidad(self, inmueble_id: int, unidad_id: int) -> None:
        self.db.query(UnidadInmueble)\
            .filter(UnidadInmueble.InmuebleId == inmueble_id, UnidadInmueble.UnidadId == unidad_id)\
            .delete(synchronize_session=False)
        self.db.commit()
