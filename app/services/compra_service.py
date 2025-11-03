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


def _col_exists(db: Session, schema: str, table: str, column: str) -> bool:
    """Chequea si existe una columna en SQL Server usando sys.columns (seguro y rápido)."""
    try:
        row = db.execute(
            text(
                """
                SELECT 1
                FROM sys.columns c
                WHERE c.object_id = OBJECT_ID(:schema_table)
                  AND c.name = :col
                """
            ),
            {"schema_table": f"{schema}.{table}", "col": column},
        ).first()
        return bool(row)
    except Exception as ex:
        Log.warning("COL_EXISTS failed for %s.%s.%s: %s", schema, table, column, ex)
        return False


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
        edificio_id: Optional[int] = None,  # ignorado en el listado
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
            where_parts.append(
                """
                EXISTS (
                    SELECT 1
                    FROM dbo.Divisiones d WITH (NOLOCK)
                    WHERE d.Id = c.DivisionId
                      AND d.ServicioId = :servicio_id
                )
                """
            )
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
            where_parts.append(
                """
                EXISTS (
                    SELECT 1
                    FROM dbo.CompraMedidor cm WITH (NOLOCK)
                    WHERE cm.CompraId = c.Id
                      AND cm.MedidorId = :medidor_id
                )
                """
            )
            params["medidor_id"] = int(medidor_id)

        if region_id is not None:
            # Región desde Edificio -> (Comunas) -> Regiones (si existen)
            where_parts.append(
                """
                EXISTS (
                    SELECT 1
                    FROM dbo.Divisiones d WITH (NOLOCK)
                    LEFT JOIN dbo.Edificios efi      WITH (NOLOCK) ON efi.Id = d.EdificioId
                    LEFT JOIN dbo.Comunas com        WITH (NOLOCK) ON com.Id = efi.ComunaId
                    WHERE d.Id = c.DivisionId
                      AND com.RegionId = :region_id
                )
                """
            )
            params["region_id"] = int(region_id)

        if nombre_opcional:
            where_parts.append(
                """
                EXISTS (
                    SELECT 1
                    FROM dbo.Divisiones d WITH (NOLOCK)
                    WHERE d.Id = c.DivisionId
                      AND LOWER(ISNULL(d.Nombre,'')) LIKE LOWER(:nombre_opcional_like)
                )
                """
            )
            params["nombre_opcional_like"] = f"%{nombre_opcional}%"

        where_sql = " AND ".join(where_parts)
        size = max(1, min(200, page_size))
        offset = (page - 1) * size

        total = int(
            db.execute(
                text(
                    f"""
                    SELECT COUNT_BIG(1)
                    FROM dbo.Compras c WITH (NOLOCK)
                    WHERE {where_sql}
                    OPTION (RECOMPILE)
                    """
                ),
                params,
            ).scalar()
            or 0
        )

        rs = (
            db.execute(
                text(
                    f"""
                SELECT
                    c.Id, c.DivisionId, c.EnergeticoId, c.NumeroClienteId,
                    c.FechaCompra, c.Consumo, c.Costo,
                    c.InicioLectura, c.FinLectura, c.Active
                FROM dbo.Compras c WITH (NOLOCK)
                WHERE {where_sql}
                ORDER BY c.FechaCompra DESC, c.Id DESC
                OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY
                OPTION (RECOMPILE)
                """
                ),
                {**params, "offset": offset, "size": size},
            )
            .mappings()
            .all()
        )

        items: List[dict] = []
        for r in rs:
            items.append(
                {
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
                }
            )
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
            payload.append(
                {
                    "Consumo": float(it.Consumo),
                    "MedidorId": int(it.MedidorId),
                    "CompraId": int(obj.Id),
                    "ParametroMedicionId": int(it.ParametroMedicionId) if it.ParametroMedicionId is not None else None,
                    "UnidadMedidaId": int(it.UnidadMedidaId) if it.UnidadMedidaId is not None else None,
                }
            )

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

    # ======================================================================
    # DETALLE ENRIQUECIDO
    # ======================================================================
    def get_full(self, db: Session, compra_id: int) -> dict:
        """
        Devuelve el formato que espera el response_model:
        - Campos de la compra en el nivel raíz (aplanados)
        - Secciones extra (Items, Division, Servicio, etc.) como campos adyacentes
        """
        ctx = self.get_context(db, compra_id)

        required_root = [
            "Id",
            "DivisionId",
            "EnergeticoId",
            "NumeroClienteId",
            "FechaCompra",
            "Consumo",
            "Costo",
            "InicioLectura",
            "FinLectura",
            "FacturaId",
            "CreatedByDivisionId",
            "EstadoValidacionId",
            "Observacion",
            "Active",
            "UnidadMedidaId",
            "ServicioId",
            "ServicioNombre",
            "InstitucionId",
            "RegionId",
            "EdificioId",
            "NombreOpcional",
            "UnidadReportaPMG",
            "MedidorIds",
            "PrimerMedidorId",
        ]

        base = ctx.get("Compra", {}) if isinstance(ctx, dict) else {}
        out: Dict[str, Any] = {}

        for k in required_root:
            out[k] = base.get(k, None)

        for k, v in base.items():
            if k not in out:
                out[k] = v

        for k, v in ctx.items():
            if k == "Compra":
                continue
            out[k] = v

        div = ctx.get("Division") or {}
        serv = ctx.get("Servicio") or {}
        comu = ctx.get("Comuna") or {}
        reg = ctx.get("Region") or {}

        out["ServicioId"] = div.get("ServicioId")
        out["ServicioNombre"] = serv.get("ServicioNombre")
        out["InstitucionId"] = div.get("InstitucionId")
        out["RegionId"] = comu.get("RegionId") or (reg.get("Id") if reg else None)
        out["EdificioId"] = div.get("EdificioId")
        out["UnidadReportaPMG"] = div.get("UnidadReportaPMG")

        out.setdefault("NombreOpcional", None)
        out["MedidorIds"] = [it.get("MedidorId") for it in out.get("Items", []) if it and it.get("MedidorId") is not None]
        out["PrimerMedidorId"] = out["MedidorIds"][0] if out["MedidorIds"] else None

        return out

    def get_context(self, db: Session, compra_id: int) -> dict:
        """
        Detalle enriquecido:
          - compra base y referencias (división/servicio/institución/edificio/comuna/región/num-cliente/energético)
          - items + medidor
        Usa LEFT JOIN + NOLOCK para asemejar .NET y reduce idas a la BD.
        """

        # ====== Detección dinámica de columnas para Dirección ======
        has_efi_calle = _col_exists(db, "dbo", "Edificios", "Calle")
        has_efi_numero = _col_exists(db, "dbo", "Edificios", "Numero")
        has_efi_dirlibre = _col_exists(db, "dbo", "Edificios", "DireccionLibre")
        has_efi_direccion = _col_exists(db, "dbo", "Edificios", "Direccion")  # fallback si no hay DireccionLibre
        has_efi_comuna = _col_exists(db, "dbo", "Edificios", "ComunaId")

        # SELECT fields para Edificios.* (Dirección)
        edi_fields: List[str] = ["efi.Id AS EDI_Id"]
        edi_fields.append("efi.Calle AS EDI_Calle" if has_efi_calle else "NULL AS EDI_Calle")
        edi_fields.append("efi.Numero AS EDI_Numero" if has_efi_numero else "NULL AS EDI_Numero")
        if has_efi_dirlibre:
            edi_fields.append("efi.DireccionLibre AS EDI_DireccionLibre")
        elif has_efi_direccion:
            edi_fields.append("efi.Direccion AS EDI_DireccionLibre")
        else:
            edi_fields.append("NULL AS EDI_DireccionLibre")
        edi_fields.append("efi.ComunaId AS EDI_ComunaId" if has_efi_comuna else "NULL AS EDI_ComunaId")

        # Campos de Comuna/Región (solo si podemos enlazar por ComunaId)
        if has_efi_comuna:
            com_fields = [
                "com.Id       AS COM_Id",
                "com.Nombre   AS COM_Nombre",
                "com.RegionId AS COM_RegionId",
            ]
            reg_fields = [
                "r.Id     AS R_Id",
                "r.Nombre AS R_Nombre",
            ]
            com_join_sql = "LEFT JOIN dbo.Comunas com        WITH (NOLOCK) ON com.Id = efi.ComunaId"
            reg_join_sql = "LEFT JOIN dbo.Regiones r         WITH (NOLOCK) ON r.Id   = com.RegionId"
        else:
            com_fields = ["NULL AS COM_Id", "NULL AS COM_Nombre", "NULL AS COM_RegionId"]
            reg_fields = ["NULL AS R_Id", "NULL AS R_Nombre"]
            com_join_sql = ""
            reg_join_sql = ""

        # ====== Cabecera + referencias (en UNA consulta) ======
        select_sql = f"""
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
                d.Id            AS D_Id,
                d.Nombre        AS D_Nombre,
                d.EdificioId    AS D_EdificioId,
                d.ServicioId    AS D_ServicioId,
                d.ReportaPMG    AS D_UnidadReportaPMG,

                -- Servicio e Institución
                s.Id            AS S_Id,
                s.Nombre        AS S_Nombre,
                s.InstitucionId AS S_InstitucionId,
                i.Id            AS I_Id,
                i.Nombre        AS I_Nombre,

                -- Edificio (+ Dirección directa)
                {", ".join(edi_fields)},

                -- Comuna / Región (si procede)
                {", ".join(com_fields)},
                {", ".join(reg_fields)},

                -- Número de cliente
                nc.Id           AS NC_Id,
                nc.Numero       AS NC_Numero,

                -- Energético
                e.Id            AS E_Id,
                e.Nombre        AS E_Nombre
            FROM dbo.Compras c               WITH (NOLOCK)
            LEFT JOIN dbo.Divisiones    d    WITH (NOLOCK) ON d.Id   = c.DivisionId
            LEFT JOIN dbo.Servicios     s    WITH (NOLOCK) ON s.Id   = d.ServicioId
            LEFT JOIN dbo.Instituciones i    WITH (NOLOCK) ON i.Id   = s.InstitucionId
            LEFT JOIN dbo.Edificios     efi  WITH (NOLOCK) ON efi.Id = d.EdificioId
            {com_join_sql}
            {reg_join_sql}
            LEFT JOIN dbo.NumeroClientes nc  WITH (NOLOCK) ON nc.Id  = c.NumeroClienteId
            LEFT JOIN dbo.Energeticos   e    WITH (NOLOCK) ON e.Id   = c.EnergeticoId
            WHERE c.Id = :id
            OPTION (RECOMPILE)
        """

        cab = db.execute(text(select_sql), {"id": compra_id}).mappings().first()
        if not cab:
            raise HTTPException(status_code=404, detail="Compra no encontrada")

        # Normaliza compra base
        compra = {
            "Id": int(cab["C_Id"]),
            "DivisionId": int(cab["C_DivisionId"]) if cab["C_DivisionId"] is not None else None,
            "NumeroClienteId": int(cab["C_NumeroClienteId"]) if cab["C_NumeroClienteId"] is not None else None,
            "EnergeticoId": int(cab["C_EnergeticoId"]) if cab["C_EnergeticoId"] is not None else None,
            "FechaCompra": _fmt_dt(cab["C_FechaCompra"]),
            "InicioLectura": _fmt_dt(cab["C_InicioLectura"]),
            "FinLectura": _fmt_dt(cab["C_FinLectura"]),
            "Consumo": float(cab["C_Consumo"] or 0),
            "Costo": float(cab["C_Costo"] or 0),
            "Observacion": cab["C_Observacion"],
            "EstadoValidacionId": cab["C_EstadoValidacionId"],
            "FacturaId": cab["C_FacturaId"],
            "CreatedByDivisionId": cab["C_CreatedByDivisionId"],
            "UnidadMedidaId": cab["C_UnidadMedidaId"],
            "Active": bool(cab["C_Active"]),
        }

        # Secciones relacionadas
        division = None
        if cab["D_Id"] is not None:
            division = {
                "Id": int(cab["D_Id"]),
                "ServicioId": int(cab["D_ServicioId"]) if cab["D_ServicioId"] is not None else None,
                "InstitucionId": int(cab["S_InstitucionId"]) if cab["S_InstitucionId"] is not None else None,
                "EdificioId": int(cab["D_EdificioId"]) if cab["D_EdificioId"] is not None else None,
                "DivisionNombre": cab["D_Nombre"],
                "UnidadReportaPMG": bool(cab["D_UnidadReportaPMG"]) if cab["D_UnidadReportaPMG"] is not None else None,
            }

        servicio = {"Id": int(cab["S_Id"]), "ServicioNombre": cab["S_Nombre"]} if cab["S_Id"] is not None else None
        institucion = {"Id": int(cab["I_Id"]), "InstitucionNombre": cab["I_Nombre"]} if cab["I_Id"] is not None else None

        comuna = None
        if cab.get("COM_Id") is not None:
            comuna = {
                "Id": int(cab["COM_Id"]),
                "ComunaNombre": cab["COM_Nombre"],
                "RegionId": int(cab["COM_RegionId"]) if cab["COM_RegionId"] is not None else None,
            }

        region = {"Id": int(cab["R_Id"]), "RegionNombre": cab["R_Nombre"]} if cab.get("R_Id") is not None else None

        numero_cliente = {"Id": int(cab["NC_Id"]), "NumeroClienteNumero": cab["NC_Numero"]} if cab["NC_Id"] is not None else None
        energetico = {"Id": int(cab["E_Id"]), "EnergeticoNombre": cab["E_Nombre"]} if cab["E_Id"] is not None else None

        # ====== Items + Medidor (detección de columnas) ======
        has_numero = _col_exists(db, "dbo", "Medidores", "Numero")
        has_device = _col_exists(db, "dbo", "Medidores", "DeviceId")
        has_tipo = _col_exists(db, "dbo", "Medidores", "TipoMedidorId")
        has_active = _col_exists(db, "dbo", "Medidores", "Active")

        medidor_fields = []
        medidor_fields.append("m.Numero AS MedidorNumero" if has_numero else "NULL AS MedidorNumero")
        medidor_fields.append("m.DeviceId AS MedidorDeviceId" if has_device else "NULL AS MedidorDeviceId")
        medidor_fields.append("m.TipoMedidorId AS MedidorTipoId" if has_tipo else "NULL AS MedidorTipoId")
        medidor_fields.append("m.Active AS MedidorActive" if has_active else "NULL AS MedidorActive")

        items_sql = f"""
            SELECT
                cm.Id,
                cm.CompraId,
                cm.MedidorId,
                cm.Consumo,
                cm.ParametroMedicionId,
                cm.UnidadMedidaId,
                {", ".join(medidor_fields)}
            FROM dbo.CompraMedidor cm WITH (NOLOCK)
            LEFT JOIN dbo.Medidores m WITH (NOLOCK) ON m.Id = cm.MedidorId
            WHERE cm.CompraId = :id
            ORDER BY cm.Id
            OPTION (RECOMPILE)
        """

        items_rows = db.execute(text(items_sql), {"id": compra_id}).mappings().all()

        items: List[Dict[str, Any]] = []
        for it in items_rows:
            item: Dict[str, Any] = {
                "Id": int(it["Id"]),
                "CompraId": int(it["CompraId"]),
                "MedidorId": int(it["MedidorId"]) if it["MedidorId"] is not None else None,
                "Consumo": float(it["Consumo"] or 0),
                "ParametroMedicionId": int(it["ParametroMedicionId"]) if it["ParametroMedicionId"] is not None else None,
                "UnidadMedidaId": int(it["UnidadMedidaId"]) if it["UnidadMedidaId"] is not None else None,
            }
            if it["MedidorId"] is not None:
                item["Medidor"] = {
                    "Numero": it.get("MedidorNumero"),
                    "DeviceId": it.get("MedidorDeviceId"),
                    "TipoMedidorId": it.get("MedidorTipoId"),
                    "Active": bool(it["MedidorActive"]) if it.get("MedidorActive") is not None else None,
                }
            else:
                item["Medidor"] = None
            items.append(item)

        # ====== Dirección armada desde Edificios (+ Comuna/Región si hay FK) ======
        direccion = {
            "Calle": cab.get("EDI_Calle"),
            "Numero": cab.get("EDI_Numero"),
            "DireccionLibre": cab.get("EDI_DireccionLibre"),
            "ComunaId": int(cab["COM_Id"]) if cab.get("COM_Id") is not None else None,
            "ComunaNombre": cab.get("COM_Nombre"),
            "RegionId": int(cab["R_Id"]) if cab.get("R_Id") is not None else None,
            "RegionNombre": cab.get("R_Nombre"),
        } if cab.get("EDI_Id") is not None else None

        # Contexto final
        contexto = {
            "Compra": compra,
            "Division": division,
            "Servicio": servicio,
            "Institucion": institucion,
            "Comuna": comuna,
            "Region": region,
            "NumeroCliente": numero_cliente,
            "Energetico": energetico,
            "Direccion": direccion,
            "Items": items,
        }
        return contexto

    # ======================================================================
    # LISTA ENRIQUECIDA (paginada) - MISMO set de filtros
    # ======================================================================
    def list_full(
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
        edificio_id: Optional[int] = None,       # no lo forzamos; queda reservado
        nombre_opcional: Optional[str] = None,
    ) -> Tuple[int, List[dict]]:
        # Aísla como .NET
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;"))

        where_parts: list[str] = ["1=1"]
        params: dict[str, Any] = {}

        if active is not None:
            where_parts.append("c.Active = :active")
            params["active"] = 1 if active else 0

        if division_id is not None:
            where_parts.append("c.DivisionId = :division_id")
            params["division_id"] = int(division_id)

        if servicio_id is not None:
            where_parts.append(
                """
                EXISTS (
                  SELECT 1 FROM dbo.Divisiones d WITH (NOLOCK)
                  WHERE d.Id = c.DivisionId AND d.ServicioId = :servicio_id
                )
                """
            )
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
            where_parts.append(
                """
                EXISTS (
                    SELECT 1
                    FROM dbo.CompraMedidor cm WITH (NOLOCK)
                    WHERE cm.CompraId = c.Id AND cm.MedidorId = :medidor_id
                )
                """
            )
            params["medidor_id"] = int(medidor_id)

        if region_id is not None:
            where_parts.append(
                """
                EXISTS (
                  SELECT 1
                  FROM dbo.Divisiones d WITH (NOLOCK)
                  LEFT JOIN dbo.Edificios efi WITH (NOLOCK)   ON efi.Id = d.EdificioId
                  LEFT JOIN dbo.Comunas  com WITH (NOLOCK)   ON com.Id = efi.ComunaId
                  WHERE d.Id = c.DivisionId AND com.RegionId = :region_id
                )
                """
            )
            params["region_id"] = int(region_id)

        if nombre_opcional:
            where_parts.append(
                """
                EXISTS (
                  SELECT 1 FROM dbo.Divisiones d WITH (NOLOCK)
                  WHERE d.Id = c.DivisionId
                    AND LOWER(ISNULL(d.Nombre,'')) LIKE LOWER(:nombre_opcional_like)
                )
                """
            )
            params["nombre_opcional_like"] = f"%{nombre_opcional}%"

        where_sql = " AND ".join(where_parts)
        size = max(1, min(200, page_size))
        offset = (page - 1) * size

        # total
        total = int(
            db.execute(
                text(
                    f"""
                    SELECT COUNT_BIG(1)
                    FROM dbo.Compras c WITH (NOLOCK)
                    WHERE {where_sql}
                    OPTION (RECOMPILE)
                    """
                ),
                params,
            ).scalar() or 0
        )

        # Detección de columnas (dirección en Edificios)
        has_efi_calle     = _col_exists(db, "dbo", "Edificios", "Calle")
        has_efi_numero    = _col_exists(db, "dbo", "Edificios", "Numero")
        has_efi_dirlibre  = _col_exists(db, "dbo", "Edificios", "DireccionLibre")
        has_efi_direccion = _col_exists(db, "dbo", "Edificios", "Direccion")  # fallback
        edi_calle   = "efi.Calle" if has_efi_calle else "NULL"
        edi_numero  = "efi.Numero" if has_efi_numero else "NULL"
        edi_dirlib  = "efi.DireccionLibre" if has_efi_dirlibre else ("efi.Direccion" if has_efi_direccion else "NULL")

        # Query enriquecida (paginada). STRING_AGG para MedidorIds y MIN para PrimerMedidorId
        sql = f"""
        WITH base AS (
          SELECT
            c.Id, c.DivisionId, c.EnergeticoId, c.NumeroClienteId,
            c.FechaCompra, c.Consumo, c.Costo, c.InicioLectura, c.FinLectura, c.Active,
            d.ServicioId                    AS ServicioId,
            s.Nombre                        AS ServicioNombre,
            s.InstitucionId                 AS InstitucionId,
            d.EdificioId                    AS EdificioId,
            d.ReportaPMG                    AS UnidadReportaPMG,
            d.Nombre                        AS DivisionNombre,
            {edi_calle}                     AS EDI_Calle,
            {edi_numero}                    AS EDI_Numero,
            {edi_dirlib}                    AS EDI_DireccionLibre,
            com.Id                          AS COM_Id,
            com.Nombre                      AS COM_Nombre,
            com.RegionId                    AS COM_RegionId,
            r.Id                            AS R_Id,
            r.Nombre                        AS R_Nombre,
            STRING_AGG(CAST(cm.MedidorId AS varchar(50)), ',') AS MedidoresCSV,
            MIN(cm.MedidorId)               AS PrimerMedidorId
          FROM dbo.Compras c       WITH (NOLOCK)
          LEFT JOIN dbo.Divisiones d   WITH (NOLOCK) ON d.Id   = c.DivisionId
          LEFT JOIN dbo.Servicios  s   WITH (NOLOCK) ON s.Id   = d.ServicioId
          LEFT JOIN dbo.Edificios  efi WITH (NOLOCK) ON efi.Id = d.EdificioId
          LEFT JOIN dbo.Comunas    com WITH (NOLOCK) ON com.Id = efi.ComunaId
          LEFT JOIN dbo.Regiones   r   WITH (NOLOCK) ON r.Id   = com.RegionId
          LEFT JOIN dbo.CompraMedidor cm WITH (NOLOCK) ON cm.CompraId = c.Id
          WHERE {where_sql}
          GROUP BY
            c.Id, c.DivisionId, c.EnergeticoId, c.NumeroClienteId,
            c.FechaCompra, c.Consumo, c.Costo, c.InicioLectura, c.FinLectura, c.Active,
            d.ServicioId, s.Nombre, s.InstitucionId, d.EdificioId, d.ReportaPMG, d.Nombre,
            {edi_calle}, {edi_numero}, {edi_dirlib},
            com.Id, com.Nombre, com.RegionId, r.Id, r.Nombre
        )
        SELECT *
        FROM base
        ORDER BY FechaCompra DESC, Id DESC
        OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY
        OPTION (RECOMPILE)
        """

        rows = db.execute(
            text(sql),
            {**params, "offset": offset, "size": size},
        ).mappings().all()

        items: List[dict] = []
        for r in rows:
            medidores_csv = r.get("MedidoresCSV") or ""
            medidor_ids = []
            if medidores_csv:
                try:
                    medidor_ids = [int(x) for x in medidores_csv.split(",") if x.strip().isdigit()]
                except Exception:
                    medidor_ids = []

            items.append({
                # base compra
                "Id": int(r["Id"]),
                "DivisionId": int(r["DivisionId"]) if r["DivisionId"] is not None else None,
                "EnergeticoId": int(r["EnergeticoId"]) if r["EnergeticoId"] is not None else None,
                "NumeroClienteId": int(r["NumeroClienteId"]) if r["NumeroClienteId"] is not None else None,
                "FechaCompra": _fmt_dt(r["FechaCompra"]),
                "Consumo": float(r["Consumo"] or 0),
                "Costo": float(r["Costo"] or 0),
                "InicioLectura": _fmt_dt(r["InicioLectura"]),
                "FinLectura": _fmt_dt(r["FinLectura"]),
                "Active": bool(r["Active"]),
                # enriquecidos
                "ServicioId": int(r["ServicioId"]) if r["ServicioId"] is not None else None,
                "ServicioNombre": r.get("ServicioNombre"),
                "InstitucionId": int(r["InstitucionId"]) if r["InstitucionId"] is not None else None,
                "RegionId": int(r["COM_RegionId"]) if r.get("COM_RegionId") is not None else (int(r["R_Id"]) if r.get("R_Id") is not None else None),
                "EdificioId": int(r["EdificioId"]) if r["EdificioId"] is not None else None,
                "NombreOpcional": r.get("DivisionNombre"),
                "UnidadReportaPMG": bool(r["UnidadReportaPMG"]) if r.get("UnidadReportaPMG") is not None else None,
                # medidores
                "MedidorIds": medidor_ids,
                "PrimerMedidorId": int(r["PrimerMedidorId"]) if r.get("PrimerMedidorId") is not None else (medidor_ids[0] if medidor_ids else None),
                # dirección (anidada la arma el front si hace falta; aquí retornamos RegionId arriba)
                # Si quieres devolver objeto Direccion también en el listado, descomenta:
                # "Direccion": {
                #   "Calle": r.get("EDI_Calle"),
                #   "Numero": r.get("EDI_Numero"),
                #   "DireccionLibre": r.get("EDI_DireccionLibre"),
                #   "ComunaId": int(r["COM_Id"]) if r.get("COM_Id") is not None else None,
                #   "ComunaNombre": r.get("COM_Nombre"),
                #   "RegionId": int(r["R_Id"]) if r.get("R_Id") is not None else None,
                #   "RegionNombre": r.get("R_Nombre"),
                # },
            })

        return total, items
