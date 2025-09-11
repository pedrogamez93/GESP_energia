from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, delete, extract, text
from app.db.models.compra import Compra
from app.db.models.compra_medidor import CompraMedidor

CM_TBL = CompraMedidor.__table__

def _to_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.strptime(s[:10], "%Y-%m-%d")

def _fmt_dt(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.replace(microsecond=0).isoformat()

class CompraService:
    def list(
        self,
        db: Session,
        q: Optional[str],
        page: int,
        page_size: int,
        division_id: Optional[int] = None,
        energetico_id: Optional[int] = None,
        numero_cliente_id: Optional[int] = None,
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        active: Optional[bool] = True,
    ) -> Tuple[int, List[dict]]:
        # Evitar bloqueos de lectura grandes (equivalente al NOLOCK de EF/Dapper)
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;"))

        where_parts: list[str] = ["1=1"]
        params: dict = {}

        if active is not None:
            where_parts.append("c.Active = :active")
            params["active"] = 1 if active else 0
        if division_id is not None:
            where_parts.append("c.DivisionId = :division_id")
            params["division_id"] = int(division_id)
        if energetico_id is not None:
            where_parts.append("c.EnergeticoId = :energetico_id")
            params["energetico_id"] = int(energetico_id)
        if numero_cliente_id is not None:
            where_parts.append("c.NumeroClienteId = :numero_cliente_id")
            params["numero_cliente_id"] = int(numero_cliente_id)
        if fecha_desde:
            where_parts.append("c.FechaCompra >= :desde")
            params["desde"] = _to_dt(fecha_desde)
        if fecha_hasta:
            where_parts.append("c.FechaCompra < :hasta")
            params["hasta"] = _to_dt(fecha_hasta)
        if q:
            where_parts.append("LOWER(ISNULL(c.Observacion,'')) LIKE LOWER(:q_like)")
            params["q_like"] = f"%{q}%"

        where_sql = " AND ".join(where_parts)
        size = max(1, min(200, page_size))
        offset = (page - 1) * size

        count_sql = f"""
            SELECT COUNT_BIG(1)
            FROM dbo.Compras c WITH (NOLOCK)
            WHERE {where_sql}
            OPTION (RECOMPILE)
        """
        total = int(db.execute(text(count_sql), params).scalar() or 0)

        rows_sql = f"""
            SELECT
                c.Id, c.DivisionId, c.EnergeticoId, c.NumeroClienteId,
                c.FechaCompra, c.Consumo, c.Costo, c.InicioLectura, c.FinLectura, c.Active
            FROM dbo.Compras c WITH (NOLOCK)
            WHERE {where_sql}
            ORDER BY c.FechaCompra DESC, c.Id DESC
            OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY
            OPTION (RECOMPILE)
        """
        rows_params = dict(params); rows_params.update({"offset": offset, "size": size})
        rs = db.execute(text(rows_sql), rows_params).mappings().all()

        items: List[dict] = []
        for r in rs:
            items.append({
                "Id": int(r["Id"]),
                "DivisionId": int(r["DivisionId"]),
                "EnergeticoId": int(r["EnergeticoId"]),
                "NumeroClienteId": int(r["NumeroClienteId"]) if r["NumeroClienteId"] is not None else None,
                "FechaCompra": _fmt_dt(r["FechaCompra"]),
                "Consumo": float(r["Consumo"] or 0),
                "Costo": float(r["Costo"] or 0),
                "InicioLectura": _fmt_dt(r["InicioLectura"]),
                "FinLectura": _fmt_dt(r["FinLectura"]),
                "Active": bool(r["Active"]),
            })
        return total, items

    def get(self, db: Session, compra_id: int) -> Compra:
        obj = db.query(Compra).filter(Compra.Id == compra_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Compra no encontrada")
        return obj

    def _items_by_compra(self, db: Session, compra_id: int) -> List[CompraMedidor]:
        return (
            db.query(CompraMedidor)
            .filter(CompraMedidor.CompraId == compra_id)
            .order_by(CompraMedidor.Id)
            .all()
        )

    def create(self, db: Session, data, created_by: Optional[str] = None) -> Tuple[Compra, List[CompraMedidor]]:
        now = datetime.utcnow()
        created_by_div = data.CreatedByDivisionId or data.DivisionId

        obj = Compra(
            CreatedAt=now, UpdatedAt=now, Version=0, Active=True,
            CreatedBy=created_by, ModifiedBy=created_by,
            Consumo=data.Consumo,
            InicioLectura=_to_dt(data.InicioLectura),
            FinLectura=_to_dt(data.FinLectura),
            DivisionId=data.DivisionId,
            EnergeticoId=data.EnergeticoId,
            FechaCompra=_to_dt(data.FechaCompra),
            Costo=data.Costo,
            FacturaId=data.FacturaId,
            NumeroClienteId=data.NumeroClienteId,
            UnidadMedidaId=data.UnidadMedidaId,
            Observacion=data.Observacion,
            EstadoValidacionId=data.EstadoValidacionId,
            CreatedByDivisionId=created_by_div,
            SinMedidor=data.SinMedidor,
        )
        db.add(obj)
        db.flush()

        payload = []
        for it in data.Items or []:
            payload.append({
                "Consumo": float(it.Consumo),
                "MedidorId": int(it.MedidorId),
                "CompraId": int(obj.Id),
                "ParametroMedicionId": int(it.ParametroMedicionId) if it.ParametroMedicionId is not None else None,
                "UnidadMedidaId": int(it.UnidadMedidaId) if it.UnidadMedidaId is not None else None,
            })
        if payload:
            db.execute(CM_TBL.insert(), payload)

        db.commit()
        db.refresh(obj)
        return obj, self._items_by_compra(db, obj.Id)

    def update(self, db: Session, compra_id: int, data, modified_by: Optional[str] = None) -> Tuple[Compra, List[CompraMedidor]]:
        obj = self.get(db, compra_id)
        payload = data.model_dump(exclude_unset=True)
        for k in ("InicioLectura", "FinLectura", "FechaCompra", "ReviewedAt"):
            if k in payload and payload[k] is not None:
                payload[k] = _to_dt(payload[k])
        for name, value in payload.items():
            setattr(obj, name, value)
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit()
        db.refresh(obj)
        return obj, self._items_by_compra(db, obj.Id)

    def soft_delete(self, db: Session, compra_id: int, modified_by: Optional[str] = None):
        obj = self.get(db, compra_id)
        if not obj.Active:
            return
        obj.Active = False
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit()

    def reactivate(self, db: Session, compra_id: int, modified_by: Optional[str] = None) -> Compra:
        obj = self.get(db, compra_id)
        if obj.Active:
            return obj
        obj.Active = True
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit()
        db.refresh(obj)
        return obj

    def replace_items(self, db: Session, compra_id: int, items: List[dict]) -> List[CompraMedidor]:
        self.get(db, compra_id)
        db.execute(delete(CM_TBL).where(CM_TBL.c.CompraId == compra_id))
        payload = []
        for it in items or []:
            payload.append({
                "Consumo": float(it["Consumo"]),
                "MedidorId": int(it["MedidorId"]),
                "CompraId": int(compra_id),
                "ParametroMedicionId": int(it["ParametroMedicionId"]) if it.get("ParametroMedicionId") is not None else None,
                "UnidadMedidaId": int(it["UnidadMedidaId"]) if it.get("UnidadMedidaId") is not None else None,
            })
        if payload:
            db.execute(CM_TBL.insert(), payload)
        db.commit()
        return self._items_by_compra(db, compra_id)

    def resumen_mensual(self, db: Session, division_id: int, energetico_id: int, desde: str, hasta: str) -> List[dict]:
        y = extract("year",  Compra.FechaCompra).label("anio")
        m = extract("month", Compra.FechaCompra).label("mes")
        rows = (
            db.query(y, m, func.sum(Compra.Consumo), func.sum(Compra.Costo))
            .filter(
                and_(
                    Compra.DivisionId == division_id,
                    Compra.EnergeticoId == energetico_id,
                    Compra.FechaCompra >= _to_dt(desde),
                    Compra.FechaCompra <  _to_dt(hasta),
                )
            )
            .group_by(y, m)
            .order_by(y.asc(), m.asc())
            .all()
        )
        return [{"Anio": int(r[0]), "Mes": int(r[1]), "Consumo": float(r[2] or 0), "Costo": float(r[3] or 0)} for r in rows]
