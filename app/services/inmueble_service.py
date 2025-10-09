from __future__ import annotations
from datetime import datetime
from typing import Optional, Tuple, List

from sqlalchemy import text, bindparam, true
from sqlalchemy.orm import Session

from app.db.models.division import Division
from app.db.models.direccion import Direccion
from app.db.models.unidad_inmueble import UnidadInmueble

from app.schemas.inmuebles import (
    InmuebleDTO, InmuebleListDTO, InmuebleCreate, InmuebleUpdate, InmuebleByAddressRequest
)
from app.schemas.direcciones import DireccionDTO


def _order_by_nombre_nulls_last_sql() -> str:
    return "CASE WHEN dv.Nombre IS NULL THEN 1 ELSE 0 END, dv.Nombre, dv.Id"


class InmuebleService:
    def __init__(self, db: Session):
        self.db = db

    # --------------- helpers ---------------
    @staticmethod
    def _to_list_dto_row(row) -> InmuebleListDTO:
        dirdto = None
        if row.get("DirId") is not None:
            dirdto = DireccionDTO(
                Id=row.get("DirId"),
                Calle=row.get("DirCalle"),
                Numero=row.get("DirNumero"),
                RegionId=row.get("DirRegionId"),
                ProvinciaId=row.get("DirProvinciaId"),
                ComunaId=row.get("DirComunaId"),
                DireccionCompleta=row.get("DirDireccionCompleta"),
            )
        return InmuebleListDTO(
            Id=row["Id"],
            Nombre=row.get("Nombre"),
            TipoInmueble=row.get("TipoInmueble"),
            ParentId=row.get("ParentId"),
            ServicioId=row.get("ServicioId"),
            Active=bool(row.get("Active")),
            RegionId=row.get("RegionId"),
            ComunaId=row.get("ComunaId"),
            Direccion=dirdto,
        )

    def _to_detail_base(self, d: Division, dir_: Direccion | None) -> InmuebleDTO:
        base = InmuebleListDTO(
            Id=d.Id,
            Nombre=d.Nombre,
            TipoInmueble=d.TipoInmueble,
            ParentId=d.ParentId,
            ServicioId=d.ServicioId,
            Active=bool(d.Active),
            RegionId=d.RegionId,
            ComunaId=d.ComunaId,
            Direccion=DireccionDTO.model_validate(dir_) if dir_ else None,
        )
        return InmuebleDTO(
            **base.model_dump(),
            AnyoConstruccion=d.AnyoConstruccion,
            Superficie=d.Superficie,
            NroRol=d.NroRol,
            GeVersion=d.GeVersion,
            Children=[], Pisos=[], Unidades=[],
        )

    # --------------- listado/filtrado (rápido) ---------------
    def list_paged(
        self,
        page: int = 1,
        page_size: int = 50,
        active: Optional[bool] = True,
        servicio_id: Optional[int] = None,
        region_id: Optional[int] = None,
        comuna_id: Optional[int] = None,
        tipo_inmueble: Optional[int] = None,
        direccion: Optional[str] = None,
        search: Optional[str] = None,
        gev: Optional[int] = 3,
    ) -> Tuple[int, List[InmuebleListDTO]]:

        where_parts: List[str] = ["1=1"]
        params: dict = {}
        if active is not None:
            where_parts.append("dv.Active = :active")
            params["active"] = 1 if active else 0
        if gev is not None:
            where_parts.append("dv.GeVersion = :gev")
            params["gev"] = gev
        if servicio_id is not None:
            where_parts.append("dv.ServicioId = :servicio_id")
            params["servicio_id"] = servicio_id
        if region_id is not None:
            where_parts.append("dv.RegionId = :region_id")
            params["region_id"] = region_id
        if comuna_id is not None:
            where_parts.append("dv.ComunaId = :comuna_id")
            params["comuna_id"] = comuna_id
        if tipo_inmueble is not None:
            where_parts.append("dv.TipoInmueble = :tipo_inmueble")
            params["tipo_inmueble"] = tipo_inmueble

        join_dir_for_filter = ""
        if direccion:
            where_parts.append(
                "(LOWER(ISNULL(di.Calle,'')) LIKE LOWER(:direccion_like) "
                "OR LOWER(ISNULL(di.Numero,'')) LIKE LOWER(:direccion_like))"
            )
            params["direccion_like"] = f"%{direccion}%"
            join_dir_for_filter = "LEFT JOIN dbo.Direcciones di WITH (NOLOCK) ON di.Id = dv.DireccionInmuebleId"
        if search:
            where_parts.append(
                "(LOWER(ISNULL(dv.Nombre,'')) LIKE LOWER(:like) "
                "OR LOWER(ISNULL(dv.NroRol,'')) LIKE LOWER(:like) "
                "OR LOWER(ISNULL(di.DireccionCompleta,'')) LIKE LOWER(:like))"
            )
            params["like"] = f"%{search}%"
            if "di WITH (NOLOCK)" not in join_dir_for_filter:
                join_dir_for_filter = "LEFT JOIN dbo.Direcciones di WITH (NOLOCK) ON di.Id = dv.DireccionInmuebleId"

        where_sql = " AND ".join(where_parts)
        size = max(1, min(200, page_size))
        offset = (page - 1) * size

        count_sql = f"""
            SELECT COUNT_BIG(1) AS total
            FROM dbo.Divisiones dv WITH (NOLOCK)
            {join_dir_for_filter}
            WHERE {where_sql}
        """
        total = int(self.db.execute(text(count_sql), params).scalar() or 0)

        rows_sql = f"""
            SELECT
                dv.Id, dv.Nombre, dv.TipoInmueble, dv.ParentId, dv.ServicioId, dv.Active,
                dv.RegionId, dv.ComunaId, dv.DireccionInmuebleId, dv.NroRol, dv.GeVersion,
                di.Id AS DirId, di.Calle AS DirCalle, di.Numero AS DirNumero,
                di.RegionId AS DirRegionId, di.ProvinciaId AS DirProvinciaId,
                di.ComunaId AS DirComunaId, di.DireccionCompleta AS DirDireccionCompleta
            FROM dbo.Divisiones dv WITH (NOLOCK)
            LEFT JOIN dbo.Direcciones di WITH (NOLOCK) ON di.Id = dv.DireccionInmuebleId
            WHERE {where_sql}
            ORDER BY {_order_by_nombre_nulls_last_sql()}
            OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY
        """
        rows_params = dict(params)
        rows_params.update({"offset": offset, "size": size})
        items = [
            self._to_list_dto_row(r)
            for r in self.db.execute(text(rows_sql), rows_params).mappings().all()
        ]
        return total, items

    # --------------- detalle (árbol + pisos/áreas + unidades) ---------------
    def get(self, inmueble_id: int) -> InmuebleDTO | None:
        root = (
            self.db.query(Division)
            .filter(Division.Id == inmueble_id, Division.Active == true())
            .first()
        )
        if not root:
            return None
        dir_ = (
            self.db.query(Direccion).filter(Direccion.Id == root.DireccionInmuebleId).first()
            if root.DireccionInmuebleId else None
        )
        dto = self._to_detail_base(root, dir_)
        dto.Unidades = self._fetch_unidades_por_inmueble(root.Id)
        dto.Pisos = self._fetch_pisos_for_division(root.Id)
        dto.Children = self._fetch_children_tree(root.Id) if root.TipoInmueble == 1 else []
        return dto

    def _fetch_children_tree(self, parent_id: int) -> list[InmuebleDTO]:
        childs = (
            self.db.query(Division)
            .filter(Division.ParentId == parent_id, Division.Active == true())
            .all()
        )
        result: list[InmuebleDTO] = []
        for ch in childs:
            dir_ = (
                self.db.query(Direccion).filter(Direccion.Id == ch.DireccionInmuebleId).first()
                if ch.DireccionInmuebleId else None
            )
            child = self._to_detail_base(ch, dir_)
            child.Unidades = self._fetch_unidades_por_inmueble(ch.Id)
            child.Pisos = self._fetch_pisos_for_division(ch.Id)
            child.Children = self._fetch_children_tree(ch.Id) if ch.TipoInmueble == 1 else []
            result.append(child)
        return result

    def _fetch_unidades_por_inmueble(self, inmueble_id: int) -> list[dict]:
        try:
            sql = text("""
                SELECT u.Id, u.Nombre
                FROM dbo.UnidadesInmuebles ui WITH (NOLOCK)
                JOIN dbo.Unidades u WITH (NOLOCK) ON u.Id = ui.UnidadId
                WHERE ui.InmuebleId = :iid
                ORDER BY CASE WHEN u.Nombre IS NULL THEN 1 ELSE 0 END, u.Nombre, u.Id
            """)
            return [dict(r) for r in self.db.execute(sql, {"iid": inmueble_id}).mappings().all()]
        except Exception:
            return []

    def _fetch_pisos_for_division(self, division_id: int) -> list[dict]:
        try:
            pisos_sql = text("""
                SELECT p.Id, p.DivisionId, p.Active, p.NumeroPisoId,
                       np.Numero AS PisoNumero, np.Nombre AS PisoNumeroNombre
                FROM dbo.Pisos p WITH (NOLOCK)
                LEFT JOIN dbo.NumeroPisos np WITH (NOLOCK) ON np.Id = p.NumeroPisoId
                WHERE p.DivisionId = :div_id AND ISNULL(p.Active, 0) = 1
                ORDER BY CASE WHEN np.Numero IS NULL THEN 1 ELSE 0 END, np.Numero, p.Id
            """)
            pisos = self.db.execute(pisos_sql, {"div_id": division_id}).mappings().all()
            if not pisos:
                return []

            piso_ids = [r["Id"] for r in pisos]

            areas_sql = text("""
                SELECT a.Id, a.PisoId, a.Active, a.Nombre, a.Superficie
                FROM dbo.Areas a WITH (NOLOCK)
                WHERE a.PisoId IN :ids AND ISNULL(a.Active, 0) = 1
                ORDER BY a.Id
            """).bindparams(bindparam("ids", expanding=True))
            area_rows = self.db.execute(areas_sql, {"ids": piso_ids}).mappings().all()

            areas_by_piso: dict[int, list] = {}
            area_ids: list[int] = []
            for ar in area_rows:
                area_ids.append(ar["Id"])
                areas_by_piso.setdefault(ar["PisoId"], []).append({
                    "Id": ar["Id"],
                    "Nombre": ar.get("Nombre"),
                    "Active": bool(ar.get("Active", 1)),
                    "Superficie": float(ar.get("Superficie")) if ar.get("Superficie") is not None else None,
                    "PisoId": ar["PisoId"],
                    "Unidades": [],
                })

            unidades_piso_by_piso: dict[int, list] = {}
            if piso_ids:
                up_sql = text("""
                    SELECT up.PisoId, u.Id, u.Nombre
                    FROM dbo.UnidadesPisos up WITH (NOLOCK)
                    JOIN dbo.Unidades u WITH (NOLOCK) ON u.Id = up.UnidadId
                    WHERE up.PisoId IN :ids
                    ORDER BY up.PisoId, u.Nombre, u.Id
                """).bindparams(bindparam("ids", expanding=True))
                for r in self.db.execute(up_sql, {"ids": piso_ids}).mappings():
                    unidades_piso_by_piso.setdefault(r["PisoId"], []).append({"Id": r["Id"], "Nombre": r["Nombre"]})

            unidades_area_by_area: dict[int, list] = {}
            if area_ids:
                ua_sql = text("""
                    SELECT ua.AreaId, u.Id, u.Nombre
                    FROM dbo.UnidadesAreas ua WITH (NOLOCK)
                    JOIN dbo.Unidades u WITH (NOLOCK) ON u.Id = ua.UnidadId
                    WHERE ua.AreaId IN :ids
                    ORDER BY ua.AreaId, u.Nombre, u.Id
                """).bindparams(bindparam("ids", expanding=True))
                for r in self.db.execute(ua_sql, {"ids": area_ids}).mappings():
                    unidades_area_by_area.setdefault(r["AreaId"], []).append({"Id": r["Id"], "Nombre": r["Nombre"]})

            pisos_res: list[dict] = []
            for p in pisos:
                pid = p["Id"]
                areas = areas_by_piso.get(pid, [])
                for a in areas:
                    a["Unidades"] = unidades_area_by_area.get(a["Id"], [])
                pisos_res.append({
                    "Id": pid,
                    "DivisionId": p.get("DivisionId"),
                    "PisoNumero": p.get("PisoNumero"),
                    "PisoNumeroNombre": p.get("PisoNumeroNombre"),
                    "Active": True,
                    "Areas": areas,
                    "Unidades": unidades_piso_by_piso.get(pid, []),
                })
            return pisos_res
        except Exception:
            return []

    # --------------- CRUD ---------------
    def _ensure_direccion(self, payload: DireccionDTO | None, parent: Division | None) -> int | None:
        if payload is None and parent is None:
            return None
        if payload is None and parent is not None and parent.DireccionInmuebleId:
            return parent.DireccionInmuebleId
        if payload:
            dir_ = Direccion(
                Calle=payload.Calle,
                Numero=payload.Numero,
                RegionId=payload.RegionId or 0,
                ProvinciaId=payload.ProvinciaId or 0,
                ComunaId=payload.ComunaId or 0,
                DireccionCompleta=payload.DireccionCompleta,
            )
            self.db.add(dir_); self.db.flush()
            return dir_.Id
        return None

    def create(self, data: InmuebleCreate, created_by: str) -> InmuebleDTO:
        parent = self.db.query(Division).filter(Division.Id == data.ParentId).first() if data.ParentId else None
        dir_id = self._ensure_direccion(data.Direccion, parent)
        now = datetime.utcnow()
        obj = Division(
            CreatedAt=now, UpdatedAt=now, Version=1, Active=True,
            CreatedBy=created_by, ModifiedBy=created_by,
            TipoInmueble=data.TipoInmueble, Nombre=data.Nombre, AnyoConstruccion=data.AnyoConstruccion,
            ServicioId=data.ServicioId, TipoPropiedadId=data.TipoPropiedadId, EdificioId=data.EdificioId,
            Superficie=data.Superficie, TipoUsoId=data.TipoUsoId, TipoAdministracionId=data.TipoAdministracionId,
            AdministracionServicioId=data.AdministracionServicioId, ParentId=data.ParentId, NroRol=data.NroRol,
            DireccionInmuebleId=dir_id,
        )
        self.db.add(obj); self.db.commit(); self.db.refresh(obj)
        dir_ = self.db.query(Direccion).filter(Direccion.Id == obj.DireccionInmuebleId).first() if obj.DireccionInmuebleId else None
        return self._to_detail_base(obj, dir_)

    def update(self, inmueble_id: int, data: InmuebleUpdate, modified_by: str) -> InmuebleDTO | None:
        obj = self.db.query(Division).filter(Division.Id == inmueble_id).first()
        if not obj:
            return None
        parent = self.db.query(Division).filter(Division.Id == data.ParentId).first() if data.ParentId else None
        if data.Direccion is not None:
            if obj.DireccionInmuebleId:
                dir_ = self.db.query(Direccion).filter(Direccion.Id == obj.DireccionInmuebleId).first()
                if dir_:
                    for k, v in data.Direccion.model_dump(exclude_unset=True).items():
                        setattr(dir_, k, v)
            else:
                obj.DireccionInmuebleId = self._ensure_direccion(data.Direccion, parent)
        for k, v in data.model_dump(exclude_unset=True, exclude={"Direccion"}).items():
            setattr(obj, k, v)
        obj.UpdatedAt = datetime.utcnow(); obj.ModifiedBy = modified_by; obj.Version = (obj.Version or 0) + 1
        self.db.commit(); self.db.refresh(obj)
        dir_ = self.db.query(Direccion).filter(Direccion.Id == obj.DireccionInmuebleId).first() if obj.DireccionInmuebleId else None
        return self._to_detail_base(obj, dir_)

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

        if obj.TipoInmueble == 1:
            self.db.query(Division).filter(
                Division.ParentId == inmueble_id,
                Division.Active == true()
            ).update({Division.Active: False}, synchronize_session=False)

        self.db.commit()
        return self.get(inmueble_id)

    # --------------- compat .NET V1 ---------------
    def get_by_address(self, req: InmuebleByAddressRequest) -> List[InmuebleListDTO]:
        dir_ = self.db.query(Direccion).filter(
            Direccion.Calle == req.Calle,
            Direccion.Numero == req.Numero,
            Direccion.ComunaId == req.ComunaId
        ).first()
        if not dir_:
            return []
        inmuebles = self.db.query(Division).filter(
            Division.DireccionInmuebleId == dir_.Id,
            Division.Active == true()
        ).all()
        return [self._to_list_dto_row({
            "Id": i.Id, "Nombre": i.Nombre, "TipoInmueble": i.TipoInmueble,
            "ParentId": i.ParentId, "ServicioId": i.ServicioId, "Active": i.Active,
            "RegionId": i.RegionId, "ComunaId": i.ComunaId,
            "DirId": dir_.Id, "DirCalle": dir_.Calle, "DirNumero": dir_.Numero,
            "DirRegionId": dir_.RegionId, "DirProvinciaId": dir_.ProvinciaId,
            "DirComunaId": dir_.ComunaId, "DirDireccionCompleta": dir_.DireccionCompleta
        }) for i in inmuebles]

    # --------------- vínculos Unidad <-> Inmueble ---------------
    def add_unidad(self, inmueble_id: int, unidad_id: int) -> None:
        exists = self.db.query(UnidadInmueble).filter(
            UnidadInmueble.InmuebleId == inmueble_id,
            UnidadInmueble.UnidadId == unidad_id
        ).first()
        if exists:
            return
        self.db.add(UnidadInmueble(InmuebleId=inmueble_id, UnidadId=unidad_id))
        self.db.commit()

    def remove_unidad(self, inmueble_id: int, unidad_id: int) -> None:
        self.db.query(UnidadInmueble).filter(
            UnidadInmueble.InmuebleId == inmueble_id,
            UnidadInmueble.UnidadId == unidad_id
        ).delete(synchronize_session=False)
        self.db.commit()
