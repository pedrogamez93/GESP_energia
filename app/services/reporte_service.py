from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, select, exists

from app.db.models.compra import Compra
from app.db.models.compra_medidor import CompraMedidor
from app.db.models.medidor import Medidor
from app.db.models.numero_cliente import NumeroCliente

def _to_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.strptime(s[:10], "%Y-%m-%d")

class ReporteService:
    def serie_mensual(self, db: Session, division_id: int, energetico_id: int, desde: str, hasta: str) -> List[Dict]:
        y = func.extract("year",  Compra.FechaCompra).label("anio")
        m = func.extract("month", Compra.FechaCompra).label("mes")
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

    def consumo_por_medidor(self, db: Session,
                            division_id: Optional[int] = None,
                            energetico_id: Optional[int] = None,
                            desde: Optional[str] = None,
                            hasta: Optional[str] = None) -> List[Dict]:
        q = (
            db.query(
                CompraMedidor.MedidorId.label("MedidorId"),
                func.sum(CompraMedidor.Consumo).label("Consumo"),
                func.sum(
                    func.coalesce((CompraMedidor.Consumo / func.nullif(Compra.Consumo, 0)) * Compra.Costo, 0.0)
                ).label("Costo"),
                Medidor.Numero.label("Numero"),
                Medidor.NumeroClienteId.label("NumeroClienteId"),
            )
            .join(Compra, CompraMedidor.CompraId == Compra.Id)
            .outerjoin(Medidor, Medidor.Id == CompraMedidor.MedidorId)
        )
        if division_id is not None: q = q.filter(Compra.DivisionId == division_id)
        if energetico_id is not None: q = q.filter(Compra.EnergeticoId == energetico_id)
        if desde: q = q.filter(Compra.FechaCompra >= _to_dt(desde))
        if hasta: q = q.filter(Compra.FechaCompra < _to_dt(hasta))

        rows = (q.group_by(CompraMedidor.MedidorId, Medidor.Numero, Medidor.NumeroClienteId)
                  .order_by(func.sum(CompraMedidor.Consumo).desc())
                  .all())
        return [{"MedidorId": int(r[0]), "Consumo": float(r[1] or 0), "Costo": float(r[2] or 0),
                 "Numero": r[3], "NumeroClienteId": r[4]} for r in rows]

    def consumo_por_num_cliente(self, db: Session,
                                division_id: Optional[int] = None,
                                energetico_id: Optional[int] = None,
                                desde: Optional[str] = None,
                                hasta: Optional[str] = None) -> List[Dict]:
        qa = (
            db.query(
                Medidor.NumeroClienteId.label("NCId"),
                func.sum(CompraMedidor.Consumo).label("Consumo"),
                func.sum(
                    func.coalesce((CompraMedidor.Consumo / func.nullif(Compra.Consumo, 0)) * Compra.Costo, 0.0)
                ).label("Costo"),
            )
            .join(Compra, CompraMedidor.CompraId == Compra.Id)
            .join(Medidor, Medidor.Id == CompraMedidor.MedidorId)
        )
        if division_id is not None: qa = qa.filter(Compra.DivisionId == division_id)
        if energetico_id is not None: qa = qa.filter(Compra.EnergeticoId == energetico_id)
        if desde: qa = qa.filter(Compra.FechaCompra >= _to_dt(desde))
        if hasta: qa = qa.filter(Compra.FechaCompra < _to_dt(hasta))
        qa = qa.group_by(Medidor.NumeroClienteId)

        agregados: Dict[int, Dict[str, float]] = {}
        for ncid, cons, cost in qa.all():
            if ncid is None: continue
            agregados.setdefault(int(ncid), {"Consumo": 0.0, "Costo": 0.0})
            agregados[int(ncid)]["Consumo"] += float(cons or 0)
            agregados[int(ncid)]["Costo"]   += float(cost or 0)

        exists_items = exists(select(CompraMedidor.Id).where(CompraMedidor.CompraId == Compra.Id))
        qb = db.query(Compra.NumeroClienteId, func.sum(Compra.Consumo), func.sum(Compra.Costo)).filter(
            Compra.NumeroClienteId.isnot(None),
            ~exists_items,
        )
        if division_id is not None: qb = qb.filter(Compra.DivisionId == division_id)
        if energetico_id is not None: qb = qb.filter(Compra.EnergeticoId == energetico_id)
        if desde: qb = qb.filter(Compra.FechaCompra >= _to_dt(desde))
        if hasta: qb = qb.filter(Compra.FechaCompra < _to_dt(hasta))
        qb = qb.group_by(Compra.NumeroClienteId)

        for ncid, cons, cost in qb.all():
            if ncid is None: continue
            agregados.setdefault(int(ncid), {"Consumo": 0.0, "Costo": 0.0})
            agregados[int(ncid)]["Consumo"] += float(cons or 0)
            agregados[int(ncid)]["Costo"]   += float(cost or 0)

        if not agregados: return []
        nc_rows = db.query(NumeroCliente.Id, NumeroCliente.NombreCliente).filter(
            NumeroCliente.Id.in_(list(agregados.keys()))
        ).all()
        nombres = {int(i): n for i, n in nc_rows}

        salida = [{"NumeroClienteId": ncid,
                   "NumeroCliente": nombres.get(ncid),
                   "Consumo": round(vals["Consumo"], 6),
                   "Costo": round(vals["Costo"], 6)} for ncid, vals in agregados.items()]
        salida.sort(key=lambda x: x["Consumo"], reverse=True)
        return salida

    def kpis(self, db: Session,
             division_id: Optional[int] = None,
             energetico_id: Optional[int] = None,
             desde: Optional[str] = None,
             hasta: Optional[str] = None) -> Dict:
        q = db.query(func.sum(Compra.Consumo), func.sum(Compra.Costo))
        if division_id is not None: q = q.filter(Compra.DivisionId == division_id)
        if energetico_id is not None: q = q.filter(Compra.EnergeticoId == energetico_id)
        if desde: q = q.filter(Compra.FechaCompra >= _to_dt(desde))
        if hasta: q = q.filter(Compra.FechaCompra < _to_dt(hasta))
        cons, cost = q.first() or (0, 0)
        cons, cost = float(cons or 0), float(cost or 0)
        cu = (cost / cons) if cons else 0.0
        return {"ConsumoTotal": cons, "CostoTotal": cost, "CostoUnitario": cu}
