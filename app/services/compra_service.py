# app/services/compra_service.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, delete, extract, text

from app.db.models.compra import Compra
from app.db.models.compra_medidor import CompraMedidor

CM_TBL = CompraMedidor.__table__


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


class CompraService:
    # ─────────────────────────────────────────────────────────────────────────────
    # LISTA BÁSICA (paginada)
    # ─────────────────────────────────────────────────────────────────────────────
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
        # extras
        medidor_id: Optional[int] = None,
        estado_validacion_id: Optional[str] = None,
        region_id: Optional[int] = None,            # usando Divisiones.ComunaId -> Comunas.RegionId
        edificio_id: Optional[int] = None,          # ignorado
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
                  WHERE d.Id = c.DivisionId AND d.ServicioId = :servicio_id
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
                  WHERE cm.CompraId = c.Id AND cm.MedidorId = :medidor_id
                )
            """)
            params["medidor_id"] = int(medidor_id)

        # Región usando la comuna de la División (sin Direcciones aquí)
        if region_id is not None:
            where_parts.append("""
                EXISTS (
                  SELECT 1
                  FROM dbo.Divisiones d WITH (NOLOCK)
                  LEFT JOIN dbo.Comunas com WITH (NOLOCK) ON com.Id = d.ComunaId
                  WHERE d.Id = c.DivisionId AND com.RegionId = :region_id
                )
            """)
            params["region_id"] = int(region_id)

        # "NombreOpcional" mapea a Divisiones.Nombre
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
                    c.FechaCompra, c.Consumo, c.Costo, c.InicioLectura, c.FinLectura, c.Active
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

    # ─────────────────────────────────────────────────────────────────────────────
    # CRUD BÁSICO
    # ─────────────────────────────────────────────────────────────────────────────
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
        for it in (data.Items or []):
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
        for it in (items or []):
            payload.append({
                "Consumo": float(it["Consumo"]),
                "MedidorId": int(it["MedidorId"]),
                "CompraId": int(compra_id),
                "ParametroMedicionId": int(it.get("ParametroMedicionId")) if it.get("ParametroMedicionId") is not None else None,
                "UnidadMedidaId": int(it.get("UnidadMedidaId")) if it.get("UnidadMedidaId") is not None else None,
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

    # ─────────────────────────────────────────────────────────────────────────────
    # LISTA ENRIQUECIDA (buscador)
    # ─────────────────────────────────────────────────────────────────────────────
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
        edificio_id: Optional[int] = None,  # ignorado
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
                  WHERE d.Id = c.DivisionId AND d.ServicioId = :servicio_id
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
                  WHERE cm.CompraId = c.Id AND cm.MedidorId = :medidor_id
                )
            """)
            params["medidor_id"] = int(medidor_id)

        # Región vía comuna de División (simplificado)
        if region_id is not None:
            where_parts.append("""
                EXISTS (
                  SELECT 1
                  FROM dbo.Divisiones d WITH (NOLOCK)
                  LEFT JOIN dbo.Comunas com WITH (NOLOCK) ON com.Id = d.ComunaId
                  WHERE d.Id = c.DivisionId AND com.RegionId = :region_id
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

        rows_sql = f"""
            WITH base AS (
              SELECT
                  c.Id, c.DivisionId, c.EnergeticoId, c.NumeroClienteId,
                  c.FechaCompra, c.Consumo, c.Costo, c.InicioLectura, c.FinLectura,
                  c.Active, c.EstadoValidacionId
              FROM dbo.Compras c WITH (NOLOCK)
              WHERE {where_sql}
            )
            SELECT
                b.*,
                (
                  SELECT TOP 1 d.ServicioId
                  FROM dbo.Divisiones d WITH (NOLOCK)
                  WHERE d.Id = b.DivisionId
                ) AS ServicioId,
                (
                  SELECT TOP 1 s.Nombre
                  FROM dbo.Divisiones d WITH (NOLOCK)
                  LEFT JOIN dbo.Servicios s WITH (NOLOCK) ON s.Id = d.ServicioId
                  WHERE d.Id = b.DivisionId
                ) AS ServicioNombre,
                (
                  SELECT TOP 1 s.InstitucionId
                  FROM dbo.Divisiones d WITH (NOLOCK)
                  LEFT JOIN dbo.Servicios s WITH (NOLOCK) ON s.Id = d.ServicioId
                  WHERE d.Id = b.DivisionId
                ) AS InstitucionId,
                (
                  -- Región preferentemente desde Edificio->Direccion->Comuna; si no, desde la Comuna de la División
                  SELECT TOP 1 COALESCE(comDir.RegionId, comDiv.RegionId)
                  FROM dbo.Divisiones d WITH (NOLOCK)
                  LEFT JOIN dbo.Edificios e  WITH (NOLOCK) ON e.Id = d.EdificioId
                  LEFT JOIN dbo.Direcciones dir WITH (NOLOCK) ON dir.Id = e.DireccionId
                  LEFT JOIN dbo.Comunas comDir WITH (NOLOCK) ON comDir.Id = dir.ComunaId
                  LEFT JOIN dbo.Comunas comDiv WITH (NOLOCK) ON comDiv.Id = d.ComunaId
                  WHERE d.Id = b.DivisionId
                ) AS RegionId,
                CAST(NULL AS INT) AS EdificioId,
                (
                  SELECT TOP 1 d.Nombre
                  FROM dbo.Divisiones d WITH (NOLOCK)
                  WHERE d.Id = b.DivisionId
                ) AS NombreOpcional,
                (
                  SELECT TOP 1 d.ReportaPMG
                  FROM dbo.Divisiones d WITH (NOLOCK)
                  WHERE d.Id = b.DivisionId
                ) AS UnidadReportaPMG,
                (
                  SELECT TOP 1 cm.MedidorId
                  FROM dbo.CompraMedidor cm WITH (NOLOCK)
                  WHERE cm.CompraId = b.Id
                  ORDER BY cm.Id ASC
                ) AS PrimerMedidorId,
                (
                  SELECT STRING_AGG(CONVERT(varchar(32), cm.MedidorId), ',')
                  FROM dbo.CompraMedidor cm WITH (NOLOCK)
                  WHERE cm.CompraId = b.Id
                ) AS MedidorIdsCSV
            FROM base b
            ORDER BY b.FechaCompra DESC, b.Id DESC
            OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY
            OPTION (RECOMPILE)
        """

        rs = db.execute(
            text(rows_sql),
            {**params, "offset": offset, "size": size},
        ).mappings().all()

        items: List[dict] = []
        for r in rs:
            med_csv = r.get("MedidorIdsCSV") or ""
            med_list = [int(x) for x in med_csv.split(",") if x.strip().isdigit()]
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
                "EstadoValidacionId": r.get("EstadoValidacionId"),
                "ServicioId": int(r["ServicioId"]) if r.get("ServicioId") is not None else None,
                "ServicioNombre": r.get("ServicioNombre"),
                "InstitucionId": int(r["InstitucionId"]) if r.get("InstitucionId") is not None else None,
                "RegionId": int(r["RegionId"]) if r.get("RegionId") is not None else None,
                "EdificioId": int(r["EdificioId"]) if r.get("EdificioId") is not None else None,
                "NombreOpcional": r.get("NombreOpcional"),
                "UnidadReportaPMG": int(r["UnidadReportaPMG"]) if r.get("UnidadReportaPMG") is not None else None,
                "PrimerMedidorId": int(r["PrimerMedidorId"]) if r.get("PrimerMedidorId") is not None else None,
                "MedidorIds": med_list,
            })
        return total, items

    # ─────────────────────────────────────────────────────────────────────────────
    # DETALLE ENRIQUECIDO POR ID (ahora con Dirección completa)
    # ─────────────────────────────────────────────────────────────────────────────
    def get_context(self, db: Session, division_id: int, compra_id: int) -> dict:
        # Servicio / Institución desde División -> Servicio
        serv_sql = """
            SELECT TOP 1 d.ServicioId,
                        s.Nombre        AS ServicioNombre,
                        s.InstitucionId
            FROM dbo.Divisiones d WITH (NOLOCK)
            LEFT JOIN dbo.Servicios s WITH (NOLOCK) ON s.Id = d.ServicioId
            WHERE d.Id = :div_id
        """
        serv = db.execute(text(serv_sql), {"div_id": int(division_id)}).mappings().first()
        servicio_id     = int(serv["ServicioId"])     if serv and serv["ServicioId"]     is not None else None
        servicio_nombre = str(serv["ServicioNombre"]) if serv and serv["ServicioNombre"] is not None else None
        institucion_id  = int(serv["InstitucionId"])  if serv and serv["InstitucionId"]  is not None else None

        # Datos base de División (NOTA: usamos Nombre, no NombreOpcional)
        div_base_sql = """
            SELECT TOP 1
                d.EdificioId,
                d.ComunaId       AS DivComunaId,
                d.Nombre         AS DivisionNombre,
                d.ReportaPMG     AS ReportaPMG,
                d.Calle          AS DivCalle,
                d.Numero         AS DivNumero
            FROM dbo.Divisiones d WITH (NOLOCK)
            WHERE d.Id = :div_id
        """
        dbase = db.execute(text(div_base_sql), {"div_id": int(division_id)}).mappings().first()
        edificio_id        = int(dbase["EdificioId"])     if dbase and dbase["EdificioId"]     is not None else None
        div_comuna_id      = int(dbase["DivComunaId"])    if dbase and dbase["DivComunaId"]    is not None else None
        division_nombre    = str(dbase["DivisionNombre"]) if dbase and dbase["DivisionNombre"] is not None else None
        unidad_reporta_pmg = int(dbase["ReportaPMG"])     if dbase and dbase["ReportaPMG"]     is not None else None
        div_calle          = str(dbase["DivCalle"])       if dbase and dbase["DivCalle"]       is not None else None
        div_numero         = str(dbase["DivNumero"])      if dbase and dbase["DivNumero"]      is not None else None

        # Dirección preferente por EDIFICIO
        dir_row = None
        if edificio_id:
            dir_sql = """
                SELECT TOP 1
                    e.Calle                 AS Calle,
                    e.Numero                AS Numero,
                    e.Direccion             AS DireccionLibre,
                    e.ComunaId              AS ComunaId,
                    com.Nombre              AS ComunaNombre,
                    reg.Id                  AS RegionId,
                    reg.Nombre              AS RegionNombre
                FROM dbo.Edificios e WITH (NOLOCK)
                LEFT JOIN dbo.Comunas  com WITH (NOLOCK) ON com.Id = e.ComunaId
                LEFT JOIN dbo.Regiones reg WITH (NOLOCK) ON reg.Id = com.RegionId
                WHERE e.Id = :eid
            """
            dir_row = db.execute(text(dir_sql), {"eid": edificio_id}).mappings().first()

        # Fallback por DIVISIÓN si no hubiese fila de edificio
        if not dir_row:
            dir_fallback_sql = """
                SELECT TOP 1
                    d.Calle                 AS Calle,
                    d.Numero                AS Numero,
                    CAST(NULL AS NVARCHAR(200)) AS DireccionLibre,
                    d.ComunaId              AS ComunaId,
                    com.Nombre              AS ComunaNombre,
                    reg.Id                  AS RegionId,
                    reg.Nombre              AS RegionNombre
                FROM dbo.Divisiones d WITH (NOLOCK)
                LEFT JOIN dbo.Comunas  com WITH (NOLOCK) ON com.Id = d.ComunaId
                LEFT JOIN dbo.Regiones reg WITH (NOLOCK) ON reg.Id = com.RegionId
                WHERE d.Id = :div_id
            """
            dir_row = db.execute(text(dir_fallback_sql), {"div_id": int(division_id)}).mappings().first()

        direccion = {
            "Calle":          dir_row.get("Calle")  or div_calle,
            "Numero":         dir_row.get("Numero") or div_numero,
            "DireccionLibre": dir_row.get("DireccionLibre"),
            "ComunaId":       int(dir_row["ComunaId"])  if dir_row and dir_row.get("ComunaId")  is not None else div_comuna_id,
            "ComunaNombre":   dir_row.get("ComunaNombre"),
            "RegionId":       int(dir_row["RegionId"])  if dir_row and dir_row.get("RegionId")  is not None else None,
            "RegionNombre":   dir_row.get("RegionNombre"),
        }

        # Medidores de la compra
        meds_sql = """
            SELECT cm.MedidorId
            FROM dbo.CompraMedidor cm WITH (NOLOCK)
            WHERE cm.CompraId = :cid
            ORDER BY cm.Id
        """
        med_ids = [int(r[0]) for r in db.execute(text(meds_sql), {"cid": int(compra_id)}).all()]
        primer_medidor = med_ids[0] if med_ids else None

        return {
            "ServicioId":       servicio_id,
            "ServicioNombre":   servicio_nombre,
            "InstitucionId":    institucion_id,
            "RegionId":         direccion["RegionId"],  # consistente con Dirección
            "EdificioId":       edificio_id,
            "NombreOpcional":   division_nombre,        # mantenemos la clave esperada en el front
            "UnidadReportaPMG": unidad_reporta_pmg,
            "MedidorIds":       med_ids,
            "PrimerMedidorId":  primer_medidor,
            "Direccion":        direccion,
        }


    def get_full(self, db: Session, compra_id: int) -> dict:
        c = self.get(db, compra_id)
        items = self._items_by_compra(db, compra_id)
        base = {
            "Id": c.Id,
            "DivisionId": c.DivisionId,
            "EnergeticoId": c.EnergeticoId,
            "NumeroClienteId": c.NumeroClienteId,
            "FechaCompra": c.FechaCompra,
            "Consumo": c.Consumo,
            "Costo": c.Costo,
            "InicioLectura": c.InicioLectura,
            "FinLectura": c.FinLectura,
            "Active": bool(c.Active),
            "UnidadMedidaId": c.UnidadMedidaId,
            "Observacion": c.Observacion,
            "FacturaId": c.FacturaId,
            "EstadoValidacionId": c.EstadoValidacionId,
            "RevisadoPor": c.RevisadoPor,
            "ReviewedAt": c.ReviewedAt,
            "CreatedByDivisionId": c.CreatedByDivisionId,
            "ObservacionRevision": c.ObservacionRevision,
            "SinMedidor": bool(c.SinMedidor),
            "Items": [
                {
                    "Id": it.Id,
                    "Consumo": it.Consumo,
                    "MedidorId": it.MedidorId,
                    "ParametroMedicionId": it.ParametroMedicionId,
                    "UnidadMedidaId": it.UnidadMedidaId,
                } for it in items
            ],
        }
        ctx = self.get_context(db, c.DivisionId, compra_id)
        base.update(ctx)
        return base
