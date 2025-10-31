from __future__ import annotations
from datetime import datetime
from typing import Optional, Tuple, List

from sqlalchemy.orm import Session
from sqlalchemy import func, text
from fastapi import HTTPException

from app.db.models.numero_cliente import NumeroCliente


class NumeroClienteService:
    # ---------------- LISTADO (paginado) ----------------
    def list(
        self,
        db: Session,
        q: Optional[str],
        page: int,
        page_size: int,
        empresa_id: Optional[int] = None,
        tipo_tarifa_id: Optional[int] = None,
        division_id: Optional[int] = None,
        active: Optional[bool] = True,
    ) -> dict:
        query = db.query(NumeroCliente)

        if active is not None:
            query = query.filter(NumeroCliente.Active == active)

        if q:
            like = f"%{q}%"
            # usa LOWER/ILIKE de manera portable con func.lower
            query = query.filter(
                (func.lower(NumeroCliente.Numero).like(func.lower(like))) |
                (func.lower(NumeroCliente.NombreCliente).like(func.lower(like)))
            )

        if empresa_id is not None:
            query = query.filter(NumeroCliente.EmpresaDistribuidoraId == empresa_id)
        if tipo_tarifa_id is not None:
            query = query.filter(NumeroCliente.TipoTarifaId == tipo_tarifa_id)
        if division_id is not None:
            query = query.filter(NumeroCliente.DivisionId == division_id)

        total = query.count()
        items = (
            query.order_by(NumeroCliente.Numero, NumeroCliente.Id)
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    # ---------------- DETALLE BÁSICO ----------------
    def get(self, db: Session, num_cliente_id: int) -> NumeroCliente:
        obj = db.query(NumeroCliente).filter(NumeroCliente.Id == num_cliente_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Número de cliente no encontrado")
        return obj

    # ---------------- CREAR ----------------
    def create(self, db: Session, data, created_by: str | None = None) -> NumeroCliente:
        now = datetime.utcnow()
        obj = NumeroCliente(
            CreatedAt=now,
            UpdatedAt=now,
            Version=0,
            Active=True,
            CreatedBy=created_by,
            ModifiedBy=created_by,

            Numero=data.Numero,
            NombreCliente=data.NombreCliente,
            EmpresaDistribuidoraId=data.EmpresaDistribuidoraId,
            TipoTarifaId=data.TipoTarifaId,
            DivisionId=data.DivisionId,
            PotenciaSuministrada=data.PotenciaSuministrada or 0.0,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # ---------------- ACTUALIZAR ----------------
    def update(self, db: Session, num_cliente_id: int, data, modified_by: str | None = None) -> NumeroCliente:
        obj = self.get(db, num_cliente_id)
        for name, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, name, value)
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit()
        db.refresh(obj)
        return obj

    # ---------------- SOFT DELETE ----------------
    def soft_delete(self, db: Session, num_cliente_id: int, modified_by: str | None = None) -> None:
        obj = self.get(db, num_cliente_id)
        if not obj.Active:
            return
        obj.Active = False
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit()

    # ---------------- REACTIVAR ----------------
    def reactivate(self, db: Session, num_cliente_id: int, modified_by: str | None = None) -> NumeroCliente:
        obj = self.get(db, num_cliente_id)
        if obj.Active:
            return obj
        obj.Active = True
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit()
        db.refresh(obj)
        return obj

    # ---------------- DETALLE ENRIQUECIDO ----------------
    def detalle(self, db: Session, numero_cliente_id: int) -> dict:
        """
        Devuelve detalle con Servicio/Institución/Edificio/Región + Dirección
        SIN usar dbo.Direcciones (la dirección viene directo de dbo.Edificios).
        """
        # base
        base = db.execute(text("""
            SELECT TOP 1 nc.Id, nc.DivisionId, nc.Numero, nc.NombreCliente,
                           nc.EmpresaDistribuidoraId, nc.TipoTarifaId,
                           nc.PotenciaSuministrada, nc.Active,
                           nc.CreatedAt, nc.UpdatedAt, nc.Version
            FROM dbo.NumeroClientes nc WITH (NOLOCK)
            WHERE nc.Id = :id
        """), {"id": int(numero_cliente_id)}).mappings().first()
        if not base:
            raise HTTPException(status_code=404, detail="Número de cliente no encontrado")

        # contexto
        ctx = db.execute(text("""
            SELECT TOP 1
                d.ServicioId,
                s.Nombre AS ServicioNombre,
                s.InstitucionId,
                d.EdificioId,
                COALESCE(comE.RegionId, comD.RegionId) AS RegionId
            FROM dbo.Divisiones d WITH (NOLOCK)
            LEFT JOIN dbo.Servicios s WITH (NOLOCK) ON s.Id = d.ServicioId
            LEFT JOIN dbo.Edificios e WITH (NOLOCK) ON e.Id = d.EdificioId
            LEFT JOIN dbo.Comunas  comE WITH (NOLOCK) ON comE.Id = e.ComunaId
            LEFT JOIN dbo.Comunas  comD WITH (NOLOCK) ON comD.Id = d.ComunaId
            WHERE d.Id = :div_id
        """), {"div_id": int(base["DivisionId"])}).mappings().first() or {}

        # dirección desde Edificios
        direccion = None
        if ctx.get("EdificioId"):
            dirrow = db.execute(text("""
                SELECT TOP 1
                    e.Direccion AS DireccionLibre,
                    e.Calle     AS Calle,
                    e.Numero    AS Numero,
                    e.ComunaId  AS ComunaId,
                    com.Nombre  AS ComunaNombre,
                    reg.Id      AS RegionId,
                    reg.Nombre  AS RegionNombre
                FROM dbo.Edificios e WITH (NOLOCK)
                LEFT JOIN dbo.Comunas  com WITH (NOLOCK) ON com.Id = e.ComunaId
                LEFT JOIN dbo.Regiones reg WITH (NOLOCK) ON reg.Id = com.RegionId
                WHERE e.Id = :eid
            """), {"eid": int(ctx["EdificioId"])}).mappings().first()
            if dirrow:
                direccion = {
                    "DireccionLibre": dirrow.get("DireccionLibre"),
                    "Calle":          dirrow.get("Calle"),
                    "Numero":         dirrow.get("Numero"),
                    "ComunaId":       dirrow.get("ComunaId"),
                    "ComunaNombre":   dirrow.get("ComunaNombre"),
                    "RegionId":       dirrow.get("RegionId"),
                    "RegionNombre":   dirrow.get("RegionNombre"),
                }

        # armar respuesta
        return {
            "Id": int(base["Id"]),
            "Numero": base.get("Numero"),
            "NombreCliente": base.get("NombreCliente"),
            "EmpresaDistribuidoraId": base.get("EmpresaDistribuidoraId"),
            "TipoTarifaId": base.get("TipoTarifaId"),
            "DivisionId": int(base["DivisionId"]) if base.get("DivisionId") is not None else None,
            "PotenciaSuministrada": float(base.get("PotenciaSuministrada") or 0.0),
            "Active": bool(base.get("Active")),
            "CreatedAt": base.get("CreatedAt"),
            "UpdatedAt": base.get("UpdatedAt"),
            "Version": int(base.get("Version") or 0),

            "ServicioId": ctx.get("ServicioId"),
            "ServicioNombre": ctx.get("ServicioNombre"),
            "InstitucionId": ctx.get("InstitucionId"),
            "EdificioId": ctx.get("EdificioId"),
            "RegionId": ctx.get("RegionId"),
            "Direccion": direccion,
        }
