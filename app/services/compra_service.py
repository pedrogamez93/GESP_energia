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
    # ======================================================================
    # LISTA BÁSICA (paginada)
    # ======================================================================
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
        edificio_id: Optional[int] = None,  # ignorado en el query
        nombre_opcional: Optional[str] = None,
    ) -> Tuple[int, List[dict]]:
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
                    FROM dbo.Divisiones d  WITH (NOLOCK)
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

    # ======================================================================
    # CRUD BÁSICO
    # ======================================================================
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

    # ======================================================================
    # DETALLE ENRIQUECIDO
    # ======================================================================
    def get_full(self, db: Session, compra_id: int) -> dict:
        ctx = self.get_context(db, compra_id)

        # Campos raíz que tu UI espera
        required_root = [
            "Id", "DivisionId", "EnergeticoId", "NumeroClienteId",
            "FechaCompra", "Consumo", "Costo",
            "InicioLectura", "FinLectura",
            "FacturaId", "CreatedByDivisionId",
            "EstadoValidacionId", "Observacion", "Active",
            "UnidadMedidaId",
            # extras que inyectaremos abajo:
            "ServicioId", "ServicioNombre", "InstitucionId",
            "RegionId", "EdificioId", "NombreOpcional",
            "UnidadReportaPMG", "MedidorIds", "PrimerMedidorId",
        ]

        base = ctx.get("Compra", {}) if isinstance(ctx, dict) else {}
        out: Dict[str, Any] = {k: base.get(k, None) for k in required_root}

        # Copiamos cualquier otro atributo de Compra
        for k, v in base.items():
            if k not in out:
                out[k] = v

        # Inyecciones desde el contexto
        division = ctx.get("Division")
        servicio = ctx.get("Servicio")
        institucion = ctx.get("Institucion")
        region = ctx.get("Region")
        edificio = ctx.get("Edificio")
        items = ctx.get("Items") or []
        direccion = ctx.get("Direccion") or {}

        out["ServicioId"]     = servicio["Id"] if servicio else (division.get("ServicioId") if division else None)
        out["ServicioNombre"] = servicio.get("ServicioNombre") if servicio else None
        out["InstitucionId"]  = institucion["Id"] if institucion else (division.get("InstitucionId") if division else None)
        out["RegionId"]       = region["Id"] if region else None
        out["EdificioId"]     = edificio["Id"] if edificio else (division.get("EdificioId") if division else None)
        out["NombreOpcional"] = division.get("DivisionNombre") if division else None
        out["UnidadReportaPMG"] = division.get("UnidadReportaPMG") if division else None

        med_ids = [it["MedidorId"] for it in items if it.get("MedidorId") is not None]
        out["MedidorIds"] = med_ids
        out["PrimerMedidorId"] = med_ids[0] if med_ids else None

        # Reemplaza Dirección en la raíz con la enriquecida
        out["Direccion"] = {
            "Calle": direccion.get("Calle"),
            "Numero": direccion.get("Numero"),
            "DireccionLibre": direccion.get("Referencia"),
            "ComunaId": (ctx.get("Comuna") or {}).get("Id"),
            "ComunaNombre": (ctx.get("Comuna") or {}).get("Nombre"),
            "RegionId": out["RegionId"],
            "RegionNombre": (ctx.get("Region") or {}).get("Nombre"),
        }

        # Adjunta también el resto del contexto, por si tu schema lo consume
        for k, v in ctx.items():
            if k == "Compra":
                continue
            out[k] = v

        return out

    def get_context(self, db: Session, compra_id: int) -> dict:
        """
        Flujo real de tu BD:
          Compra → División (ServicioId, InstitucionId, ComunaId, EdificioId, UnidadReportaPMG/UnidadPMG, Nombre)
          Edificio → Direcciones (por EdificioId) → Comuna → Región
          + NúmeroCliente
          + Energético
          + Items (CompraMedidor) → Medidor
        """
        # 1) Cabecera + División + Servicio + Institución (nombres)
        cab = db.execute(text("""
            SELECT TOP 1
                -- Compra
                c.Id                  AS C_Id,
                c.DivisionId          AS C_DivisionId,
                c.NumeroClienteId     AS C_NumeroClienteId,
                c.EnergeticoId        AS C_EnergeticoId,
                c.FechaCompra         AS C_FechaCompra,
                c.InicioLectura       AS C_InicioLectura,
                c.FinLectura          AS C_FinLectura,
                c.Consumo             AS C_Consumo,
                c.Costo               AS C_Costo,
                c.Observacion         AS C_Observacion,
                c.EstadoValidacionId  AS C_EstadoValidacionId,
                c.FacturaId           AS C_FacturaId,
                c.CreatedByDivisionId AS C_CreatedByDivisionId,
                c.UnidadMedidaId      AS C_UnidadMedidaId,
                c.Active              AS C_Active,

                -- División
                d.Id                  AS D_Id,
                d.Nombre              AS D_Nombre,
                d.ComunaId            AS D_ComunaId,
                d.EdificioId          AS D_EdificioId,
                d.ServicioId          AS D_ServicioId,
                d.InstitucionId       AS D_InstitucionId,
                COALESCE(d.UnidadReportaPMG, d.UnidadPMG) AS D_UnidadReportaPMG,

                -- Servicio
                s.Id                  AS S_Id,
                s.Nombre              AS S_Nombre,

                -- Institución
                i.Id                  AS I_Id,
                i.Nombre              AS I_Nombre
            FROM dbo.Compras c WITH (NOLOCK)
            LEFT JOIN dbo.Divisiones    d WITH (NOLOCK) ON d.Id  = c.DivisionId
            LEFT JOIN dbo.Servicios     s WITH (NOLOCK) ON s.Id  = d.ServicioId
            LEFT JOIN dbo.Instituciones i WITH (NOLOCK) ON i.Id  = d.InstitucionId
            WHERE c.Id = :id
            OPTION (RECOMPILE)
        """), {"id": compra_id}).mappings().first()

        if not cab:
            raise HTTPException(status_code=404, detail="Compra no encontrada")

        compra = {
            "Id":                   int(cab["C_Id"]),
            "DivisionId":           int(cab["C_DivisionId"])      if cab["C_DivisionId"]     is not None else None,
            "NumeroClienteId":      int(cab["C_NumeroClienteId"]) if cab["C_NumeroClienteId"]is not None else None,
            "EnergeticoId":         int(cab["C_EnergeticoId"])    if cab["C_EnergeticoId"]   is not None else None,
            "FechaCompra":          _fmt_dt(cab["C_FechaCompra"]),
            "InicioLectura":        _fmt_dt(cab["C_InicioLectura"]),
            "FinLectura":           _fmt_dt(cab["C_FinLectura"]),
            "Consumo":              float(cab["C_Consumo"] or 0),
            "Costo":                float(cab["C_Costo"] or 0),
            "Observacion":          cab["C_Observacion"],
            "EstadoValidacionId":   cab["C_EstadoValidacionId"],
            "FacturaId":            cab["C_FacturaId"],
            "CreatedByDivisionId":  cab["C_CreatedByDivisionId"],
            "UnidadMedidaId":       cab["C_UnidadMedidaId"],
            "Active":               bool(cab["C_Active"]),
        }

        division = None
        if cab["D_Id"] is not None:
            division = {
                "Id": int(cab["D_Id"]),
                "ComunaId": int(cab["D_ComunaId"]) if cab["D_ComunaId"] is not None else None,
                "EdificioId": int(cab["D_EdificioId"]) if cab["D_EdificioId"] is not None else None,
                "ServicioId": int(cab["D_ServicioId"]) if cab["D_ServicioId"] is not None else None,
                "InstitucionId": int(cab["D_InstitucionId"]) if cab["D_InstitucionId"] is not None else None,
                "UnidadReportaPMG": cab["D_UnidadReportaPMG"],
                "DivisionNombre": cab["D_Nombre"],
            }

        servicio = None
        if cab["S_Id"] is not None:
            servicio = {"Id": int(cab["S_Id"]), "ServicioNombre": cab["S_Nombre"]}

        institucion = None
        if cab["I_Id"] is not None:
            institucion = {"Id": int(cab["I_Id"]), "InstitucionNombre": cab["I_Nombre"]}

        # 2) Edificio
        edificio = None
        if division and division.get("EdificioId") is not None:
            edificio = _safe_fetch_one(db, """
                SELECT TOP 1
                    e.Id, e.Direccion, e.Numero, e.Calle,
                    e.Latitud, e.Longitud, e.Altitud, e.TipoEdificioId
                FROM dbo.Edificios e WITH (NOLOCK)
                WHERE e.Id = :eid
            """, {"eid": division["EdificioId"]})

        # 3) Dirección (por EdificioId)
        direccion = None
        if edificio:
            direccion = _safe_fetch_one(db, """
                SELECT TOP 1
                    dir.Id, dir.Calle, dir.Numero, dir.Referencia,
                    dir.ComunaId, dir.Latitud, dir.Longitud
                FROM dbo.Direcciones dir WITH (NOLOCK)
                WHERE dir.EdificioId = :eid
                ORDER BY dir.Id DESC
            """, {"eid": edificio["Id"]})

        if not direccion and edificio:
            direccion = {
                "Id": None,
                "Calle": edificio.get("Calle"),
                "Numero": edificio.get("Numero"),
                "Referencia": edificio.get("Direccion"),
                "ComunaId": division.get("ComunaId") if division else None,
                "Latitud": edificio.get("Latitud"),
                "Longitud": edificio.get("Longitud"),
            }

        # 4) Comuna / Región desde la dirección
        comuna = None
        if direccion and direccion.get("ComunaId") is not None:
            comuna = _safe_fetch_one(db, """
                SELECT TOP 1 c.Id, c.Nombre, c.RegionId
                FROM dbo.Comunas c WITH (NOLOCK)
                WHERE c.Id = :cid
            """, {"cid": direccion["ComunaId"]})

        region = None
        if comuna and comuna.get("RegionId") is not None:
            region = _safe_fetch_one(db, """
                SELECT TOP 1 r.Id, r.Nombre, r.Numero, r.Posicion
                FROM dbo.Regiones r WITH (NOLOCK)
                WHERE r.Id = :rid
            """, {"rid": comuna["RegionId"]})

        # 5) Número de cliente
        numero_cliente = None
        if compra["NumeroClienteId"] is not None:
            numero_cliente = _safe_fetch_one(db, """
                SELECT TOP 1
                    nc.Id,
                    nc.Numero          AS Numero,
                    nc.NombreCliente   AS NombreCliente,
                    nc.EmpresaDistribuidoraId,
                    nc.TipoTarifaId,
                    nc.DivisionId
                FROM dbo.NumeroClientes nc WITH (NOLOCK)
                WHERE nc.Id = :nid
            """, {"nid": compra["NumeroClienteId"]})

        # 6) Energético
        energetico = None
        if compra["EnergeticoId"] is not None:
            energetico = _safe_fetch_one(db, """
                SELECT TOP 1
                    e.Id, e.Nombre, e.Icono, e.Multiple,
                    e.PermiteMedidor, e.PermitePotenciaSuministrada, e.PermiteTipoTarifa
                FROM dbo.Energeticos e WITH (NOLOCK)
                WHERE e.Id = :eid
            """, {"eid": compra["EnergeticoId"]})

        # 7) Ítems + Medidor
        items_rows = _safe_fetch_all(db, """
            SELECT
                cm.Id,
                cm.CompraId,
                cm.MedidorId,
                cm.Consumo,
                cm.ParametroMedicionId,
                cm.UnidadMedidaId,

                m.Numero            AS MedidorNumero,
                m.NumeroClienteId   AS MedidorNumeroClienteId,
                m.DivisionId        AS MedidorDivisionId,
                m.Fases             AS MedidorFases,
                m.Smart             AS MedidorSmart,
                m.Compartido        AS MedidorCompartido,
                m.Active            AS MedidorActive
            FROM dbo.CompraMedidor cm WITH (NOLOCK)
            LEFT JOIN dbo.Medidores m WITH (NOLOCK)
              ON m.Id = cm.MedidorId
            WHERE cm.CompraId = :cid
            ORDER BY cm.Id
        """, {"cid": compra_id})

        items = []
        for it in items_rows:
            item = {
                "Id": int(it["Id"]),
                "CompraId": int(it["CompraId"]),
                "MedidorId": int(it["MedidorId"]) if it["MedidorId"] is not None else None,
                "Consumo": float(it["Consumo"] or 0),
                "ParametroMedicionId": int(it["ParametroMedicionId"]) if it["ParametroMedicionId"] is not None else None,
                "UnidadMedidaId": int(it["UnidadMedidaId"]) if it["UnidadMedidaId"] is not None else None,
            }
            if it.get("MedidorId") is not None:
                item["Medidor"] = {
                    "Numero": it.get("MedidorNumero"),
                    "NumeroClienteId": it.get("MedidorNumeroClienteId"),
                    "DivisionId": it.get("MedidorDivisionId"),
                    "Fases": it.get("MedidorFases"),
                    "Smart": it.get("MedidorSmart"),
                    "Compartido": it.get("MedidorCompartido"),
                    "Active": bool(it["MedidorActive"]) if it.get("MedidorActive") is not None else None,
                }
            else:
                item["Medidor"] = None
            items.append(item)

        # 8) Contexto
        contexto = {
            "Compra": compra,
            "Division": division,
            "Servicio": servicio,
            "Institucion": institucion,
            "Direccion": direccion,
            "Comuna": comuna,
            "Region": region,
            "NumeroCliente": numero_cliente,
            "Energetico": energetico,
            "Edificio": edificio,
            "Items": items,
        }
        return contexto
