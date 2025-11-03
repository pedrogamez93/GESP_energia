# app/services/compra_service.py
from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Any, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.models.compra import Compra
from app.db.models.compra_medidor import CompraMedidor

Log = logging.getLogger(__name__)
CM_TBL = CompraMedidor.__table__


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _to_dt(s: str | datetime | None) -> datetime | None:
    if s is None or s == "":
        return None
    if isinstance(s, datetime):
        return s
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d")


def _fmt_dt(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.replace(microsecond=0).isoformat()


def _safe_fetch_one(db: Session, sql: str, params: Dict[str, Any]) -> Optional[dict]:
    """
    Ejecuta una consulta y devuelve un mapping() o None,
    nunca levanta excepción: loggea y sigue.
    """
    try:
        row = db.execute(text(sql), params).mappings().first()
        return dict(row) if row else None
    except Exception as ex:
        Log.warning("SAFE_FETCH_ONE failed: %s | SQL: %s | params=%s", ex, sql, params)
        return None


def _safe_fetch_all(db: Session, sql: str, params: Dict[str, Any]) -> List[dict]:
    try:
        rows = db.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]
    except Exception as ex:
        Log.warning("SAFE_FETCH_ALL failed: %s | SQL: %s | params=%s", ex, sql, params)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# CompraService
# ─────────────────────────────────────────────────────────────────────────────
class CompraService:
    # ==========================================================================
    # LISTA BÁSICA (paginada)
    # ==========================================================================
    def list(
        self,
        db: Session,
        q: Optional[str],
        page: int,
        page_size: int,
        division_id: Optional[int] = None,
        servicio_id: Optional[int] = None,
        energetico_id: Optional[int] = None,
        numero_cliente_id: Optional[int] = None,
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        active: Optional[bool] = True,
        medidor_id: Optional[int] = None,
        estado_validacion_id: Optional[str] = None,
        region_id: Optional[int] = None,
        edificio_id: Optional[int] = None,  # ignorado
        nombre_opcional: Optional[str] = None,
    ) -> Tuple[int, List[dict]]:
        # Aislamos como .NET (NOLOCK) y evitamos locks relevantes
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;"))

        where_parts: list[str] = ["1=1"]
        params: dict = {}

        if active is not None:
            where_parts.append("c.Active = :active")
            params["active"] = 1 if active else 0

        if division_id is not None:
            where_parts.append("c.DivisionId = :division_id")
            params["division_id"] = int(division_id)

        if servicio_id is not None:
            where_parts.append("""
                EXISTS (
                    SELECT 1
                    FROM dbo.Divisiones d WITH (NOLOCK)
                    WHERE d.Id = c.DivisionId
                      AND d.ServicioId = :servicio_id
                )
            """)
            params["servicio_id"] = int(servicio_id)

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

        if estado_validacion_id:
            where_parts.append("c.EstadoValidacionId = :estado_validacion_id")
            params["estado_validacion_id"] = estado_validacion_id

        if medidor_id is not None:
            where_parts.append("""
                EXISTS (
                    SELECT 1
                    FROM dbo.CompraMedidor cm WITH (NOLOCK)
                    WHERE cm.CompraId = c.Id
                      AND cm.MedidorId = :medidor_id
                )
            """)
            params["medidor_id"] = int(medidor_id)

        if region_id is not None:
            where_parts.append("""
                EXISTS (
                    SELECT 1
                    FROM dbo.Divisiones d WITH (NOLOCK)
                    LEFT JOIN dbo.Comunas com WITH (NOLOCK)
                      ON com.Id = d.ComunaId
                    WHERE d.Id = c.DivisionId
                      AND com.RegionId = :region_id
                )
            """)
            params["region_id"] = int(region_id)

        if nombre_opcional:
            where_parts.append("""
                EXISTS (
                    SELECT 1
                    FROM dbo.Divisiones d WITH (NOLOCK)
                    WHERE d.Id = c.DivisionId
                      AND LOWER(ISNULL(d.Nombre,'')) LIKE LOWER(:nombre_opcional_like)
                )
            """)
            params["nombre_opcional_like"] = f"%{nombre_opcional}%"

        where_sql = " AND ".join(where_parts)
        size = max(1, min(200, page_size))
        offset = (page - 1) * size

        total = int(
            db.execute(
                text(f"""
                    SELECT COUNT_BIG(1)
                    FROM dbo.Compras c WITH (NOLOCK)
                    WHERE {where_sql}
                    OPTION (RECOMPILE)
                """),
                params,
            ).scalar() or 0
        )

        rs = db.execute(
            text(f"""
                SELECT
                    c.Id, c.DivisionId, c.EnergeticoId, c.NumeroClienteId,
                    c.FechaCompra, c.Consumo, c.Costo,
                    c.InicioLectura, c.FinLectura, c.Active
                FROM dbo.Compras c WITH (NOLOCK)
                WHERE {where_sql}
                ORDER BY c.FechaCompra DESC, c.Id DESC
                OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY
                OPTION (RECOMPILE)
            """),
            {**params, "offset": offset, "size": size},
        ).mappings().all()

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

    # ==========================================================================
    # CRUD BÁSICO
    # ==========================================================================
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
        created_by_div = getattr(data, "CreatedByDivisionId", None) or data.DivisionId

        obj = Compra(
            CreatedAt=now,
            UpdatedAt=now,
            Version=0,
            Active=True,
            CreatedBy=created_by,
            ModifiedBy=created_by,
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
        for it in (getattr(data, "Items", None) or []):
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

        # Normaliza fechas que puedan venir como string
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
            return obj
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

    # ==========================================================================
    # DETALLE ENRIQUECIDO
    # ==========================================================================
    def get_full(self, db: Session, compra_id: int) -> dict:
        """
        Compatibilidad con el router: delega al método real de armado.
        """
        return self.get_context(db, compra_id)

    def get_context(self, db: Session, compra_id: int) -> dict:
        """
        Devuelve detalle enriquecido:
          - compra base
          - items (CompraMedidor) + datos de medidor (si existen)
          - referencias de división/servicio/institución
          - región/comuna
          - número de cliente
          - energético
          - dirección (si existiese una tabla Direcciones o similar)
        El método es tolerante a faltas de tablas/campos: loggea y sigue.
        """
        # 1) Compra base
        compra = _safe_fetch_one(db, """
            SELECT TOP 1
                c.Id, c.DivisionId, c.NumeroClienteId, c.EnergeticoId,
                c.FechaCompra, c.InicioLectura, c.FinLectura,
                c.Consumo, c.Costo, c.Observacion,
                c.EstadoValidacionId, c.Active
            FROM dbo.Compras c WITH (NOLOCK)
            WHERE c.Id = :id
        """, {"id": compra_id})
        if not compra:
            raise HTTPException(status_code=404, detail="Compra no encontrada")

        # Normaliza fechas
        for k in ("FechaCompra", "InicioLectura", "FinLectura"):
            compra[k] = _fmt_dt(compra[k])

        # 2) Items + Medidores
        items = _safe_fetch_all(db, """
            SELECT
                cm.Id,
                cm.CompraId,
                cm.MedidorId,
                cm.Consumo,
                cm.ParametroMedicionId,
                cm.UnidadMedidaId,
                -- campos de Medidores si existen
                m.Codigo       AS MedidorCodigo,
                m.Serie        AS MedidorSerie,
                m.TipoMedidorId AS MedidorTipoId,
                m.Active       AS MedidorActivo
            FROM dbo.CompraMedidor cm WITH (NOLOCK)
            LEFT JOIN dbo.Medidores m WITH (NOLOCK)
              ON m.Id = cm.MedidorId
            WHERE cm.CompraId = :id
            ORDER BY cm.Id
        """, {"id": compra_id})

        # 3) División + Servicio + Institución (si existen esos campos)
        division = _safe_fetch_one(db, """
            SELECT TOP 1
                d.Id, d.ServicioId, d.InstitucionId, d.ComunaId,
                d.Nombre AS DivisionNombre
            FROM dbo.Divisiones d WITH (NOLOCK)
            WHERE d.Id = :div_id
        """, {"div_id": compra["DivisionId"]}) if compra.get("DivisionId") else None

        servicio = _safe_fetch_one(db, """
            SELECT TOP 1 s.Id, s.Nombre AS ServicioNombre
            FROM dbo.Servicios s WITH (NOLOCK)
            WHERE s.Id = :sid
        """, {"sid": division["ServicioId"]}) if division and division.get("ServicioId") else None

        institucion = _safe_fetch_one(db, """
            SELECT TOP 1 i.Id, i.Nombre AS InstitucionNombre
            FROM dbo.Instituciones i WITH (NOLOCK)
            WHERE i.Id = :iid
        """, {"iid": division["InstitucionId"]}) if division and division.get("InstitucionId") else None

        # 4) Región/Comuna
        comuna = _safe_fetch_one(db, """
            SELECT TOP 1 c.Id, c.Nombre AS ComunaNombre, c.RegionId
            FROM dbo.Comunas c WITH (NOLOCK)
            WHERE c.Id = :cid
        """, {"cid": division["ComunaId"]}) if division and division.get("ComunaId") else None

        region = _safe_fetch_one(db, """
            SELECT TOP 1 r.Id, r.Nombre AS RegionNombre
            FROM dbo.Regiones r WITH (NOLOCK)
            WHERE r.Id = :rid
        """, {"rid": comuna["RegionId"]}) if comuna and comuna.get("RegionId") else None

        # 5) Número de cliente
        numero_cliente = _safe_fetch_one(db, """
            SELECT TOP 1 nc.Id, nc.Codigo AS NumeroClienteCodigo
            FROM dbo.NumeroClientes nc WITH (NOLOCK)
            WHERE nc.Id = :nid
        """, {"nid": compra["NumeroClienteId"]}) if compra.get("NumeroClienteId") else None

        # 6) Energético
        energetico = _safe_fetch_one(db, """
            SELECT TOP 1 e.Id, e.Nombre AS EnergeticoNombre
            FROM dbo.Energeticos e WITH (NOLOCK)
            WHERE e.Id = :eid
        """, {"eid": compra["EnergeticoId"]}) if compra.get("EnergeticoId") else None

        # 7) Dirección (si existe tabla de direcciones ligada a la división)
        direccion = _safe_fetch_one(db, """
            SELECT TOP 1
                dir.Id,
                dir.Calle,
                dir.Numero,
                dir.Referencia,
                dir.Latitud,
                dir.Longitud
            FROM dbo.Direcciones dir WITH (NOLOCK)
            WHERE dir.DivisionId = :div_id
            ORDER BY dir.Id DESC
        """, {"div_id": compra["DivisionId"]}) if division else None

        # 8) Construcción del contexto
        contexto: dict = {
            "Compra": {
                **compra,
                "Consumo": float(compra.get("Consumo") or 0),
                "Costo": float(compra.get("Costo") or 0),
                "Active": bool(compra.get("Active")),
            },
            "Division": division,
            "Servicio": servicio,
            "Institucion": institucion,
            "Comuna": comuna,
            "Region": region,
            "NumeroCliente": numero_cliente,
            "Energetico": energetico,
            "Direccion": direccion,
            "Items": [
                {
                    "Id": int(it["Id"]),
                    "CompraId": int(it["CompraId"]),
                    "MedidorId": int(it["MedidorId"]) if it["MedidorId"] is not None else None,
                    "Consumo": float(it["Consumo"] or 0),
                    "ParametroMedicionId": int(it["ParametroMedicionId"]) if it["ParametroMedicionId"] is not None else None,
                    "UnidadMedidaId": int(it["UnidadMedidaId"]) if it["UnidadMedidaId"] is not None else None,
                    "Medidor": {
                        "Codigo": it.get("MedidorCodigo"),
                        "Serie": it.get("MedidorSerie"),
                        "TipoMedidorId": it.get("MedidorTipoId"),
                        "Active": bool(it["MedidorActivo"]) if it.get("MedidorActivo") is not None else None,
                    } if it.get("MedidorId") else None,
                }
                for it in items
            ],
        }

        return contexto
