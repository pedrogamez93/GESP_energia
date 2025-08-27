from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, delete, extract

from app.db.models.compra import Compra
from app.db.models.compra_medidor import CompraMedidor


CM_TBL = CompraMedidor.__table__


# ---------------- Helpers ----------------
def _to_dt(s: str | None) -> datetime | None:
    """Convierte strings comunes (YYYY-MM-DD, ISO8601) a datetime."""
    if not s:
        return None
    try:
        # ISO 8601 / 'YYYY-MM-DDTHH:MM:SS(.mmm)(Z)'
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        # fallback: solo fecha
        return datetime.strptime(s[:10], "%Y-%m-%d")


class CompraService:
    # -------- listados --------
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
    ) -> dict:
        query = db.query(Compra)

        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(Compra.Observacion).like(func.lower(like)))

        if division_id is not None:
            query = query.filter(Compra.DivisionId == division_id)
        if energetico_id is not None:
            query = query.filter(Compra.EnergeticoId == energetico_id)
        if numero_cliente_id is not None:
            query = query.filter(Compra.NumeroClienteId == numero_cliente_id)

        # rango por FechaCompra
        if fecha_desde:
            query = query.filter(Compra.FechaCompra >= _to_dt(fecha_desde))
        if fecha_hasta:
            query = query.filter(Compra.FechaCompra < _to_dt(fecha_hasta))

        total = query.count()
        items = (
            query.order_by(Compra.FechaCompra.desc(), Compra.Id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

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

    # -------- escrituras --------
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
        db.flush()  # para obtener Id

        # Insert masivo de items
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

        # normaliza fechas si vienen como string
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

    def delete(self, db: Session, compra_id: int):
        obj = self.get(db, compra_id)
        # Limpieza explícita (además del ON DELETE CASCADE)
        db.execute(delete(CM_TBL).where(CM_TBL.c.CompraId == compra_id))
        db.delete(obj)
        db.commit()

    def replace_items(self, db: Session, compra_id: int, items: List[dict]) -> List[CompraMedidor]:
        self.get(db, compra_id)  # valida existencia
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

    # -------- resumen simple (por mes) --------
    def resumen_mensual(
        self, db: Session, division_id: int, energetico_id: int, desde: str, hasta: str
    ) -> List[dict]:
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

        return [
            {"Anio": int(r[0]), "Mes": int(r[1]), "Consumo": float(r[2] or 0), "Costo": float(r[3] or 0)}
            for r in rows
        ]
