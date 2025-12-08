# app/services/division_sistemas_service.py
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.division import Division
from app.db.models.tipo_luminaria import TipoLuminaria
from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.db.models.tipo_equipo_calefaccion_energetico import TipoEquipoCalefaccionEnergetico
from app.db.models.energetico import Energetico
from app.db.models.tipos_colectores import TipoColector  # ajusta el nombre si tu modelo se llama distinto

from app.schemas.division_sistemas import DivisionSistemasDTO, DivisionSistemasUpdate
from app.services.division_service import DivisionService

log = logging.getLogger("division_sistemas")


def _now():
    return datetime.utcnow()


class DivisionSistemasService:
    """
    Lógica del mantenedor de sistemas por División:
    - Iluminación (TipoLuminariaId)
    - Calefacción (EquipoCalefaccion*, EnergeticoCalefaccion*, TempSeteoCalefaccionId)
    - Refrigeración (EquipoRefrigeracion*, EnergeticoRefrigeracion*, TempSeteoRefrigeracionId)
    - ACS (EquipoAcs*, EnergeticoAcsId, SistemaSolarTermico, ColectorId, SupColectores, FotoTecho, SupFotoTecho,
           MantColectores)
    - Fotovoltaico (InstTerSisFv, SupInstTerSisFv, ImpSisFv, SupImptSisFv, PotIns, MantSfv)
    """

    def __init__(self) -> None:
        # Reutilizamos la lógica de DivisionService.get (normalización de Pisos, etc.)
        self._division_svc = DivisionService()

    # ------------------------------------------------------------------ #
    # GET de la División (objeto ORM)
    # ------------------------------------------------------------------ #
    def get(self, db: Session, division_id: int) -> Division:
        """
        Devuelve la entidad Division usando la lógica actual de DivisionService.
        """
        return self._division_svc.get(db, division_id)

    # ------------------------------------------------------------------ #
    # Mapear Division -> DivisionSistemasDTO (dict)
    # ------------------------------------------------------------------ #
    def to_dto(self, d: Division) -> Dict[str, Any]:
        """
        Convierte la entidad Division a un dict compatible con DivisionSistemasDTO.
        Usamos getattr para no romper si faltara algún campo en el modelo.
        """
        return {
            "DivisionId": d.Id,

            # Iluminación
            "TipoLuminariaId": getattr(d, "TipoLuminariaId", None),

            # Calefacción
            "EquipoCalefaccionId": getattr(d, "EquipoCalefaccionId", None),
            "EnergeticoCalefaccionId": getattr(d, "EnergeticoCalefaccionId", None),
            "TempSeteoCalefaccionId": getattr(d, "TempSeteoCalefaccionId", None),

            # Refrigeración
            "EquipoRefrigeracionId": getattr(d, "EquipoRefrigeracionId", None),
            "EnergeticoRefrigeracionId": getattr(d, "EnergeticoRefrigeracionId", None),
            "TempSeteoRefrigeracionId": getattr(d, "TempSeteoRefrigeracionId", None),

            # ACS
            "EquipoAcsId": getattr(d, "EquipoAcsId", None),
            "EnergeticoAcsId": getattr(d, "EnergeticoAcsId", None),
            "SistemaSolarTermico": getattr(d, "SistemaSolarTermico", None),
            "ColectorId": getattr(d, "ColectorId", None),
            "SupColectores": getattr(d, "SupColectores", None),
            "FotoTecho": getattr(d, "FotoTecho", None),
            "SupFotoTecho": getattr(d, "SupFotoTecho", None),

            # Fotovoltaico
            "InstTerSisFv": getattr(d, "InstTerSisFv", None),
            "SupInstTerSisFv": getattr(d, "SupInstTerSisFv", None),
            "ImpSisFv": getattr(d, "ImpSisFv", None),
            "SupImptSisFv": getattr(d, "SupImptSisFv", None),
            "PotIns": getattr(d, "PotIns", None),

            # Mantenciones
            "MantColectores": getattr(d, "MantColectores", None),
            "MantSfv": getattr(d, "MantSfv", None),

            "Version": getattr(d, "Version", None),
        }

    # ------------------------------------------------------------------ #
    # UPDATE parcial de los campos de sistemas
    # ------------------------------------------------------------------ #
    def update(
        self,
        db: Session,
        division_id: int,
        payload: Dict[str, Any],
        user: Optional[str] = None,
    ) -> Division:
        """
        Actualiza solo los campos de sistemas definidos en DivisionSistemasUpdate.
        `payload` ya viene filtrado con exclude_unset=True desde el router.
        """
        d = self.get(db, division_id)

        # Campos que permitimos tocar desde este mantenedor
        allowed_fields = {
            "TipoLuminariaId",
            "EquipoCalefaccionId",
            "EnergeticoCalefaccionId",
            "TempSeteoCalefaccionId",
            "EquipoRefrigeracionId",
            "EnergeticoRefrigeracionId",
            "TempSeteoRefrigeracionId",
            "EquipoAcsId",
            "EnergeticoAcsId",
            "SistemaSolarTermico",
            "ColectorId",
            "SupColectores",
            "FotoTecho",
            "SupFotoTecho",
            "InstTerSisFv",
            "SupInstTerSisFv",
            "ImpSisFv",
            "SupImptSisFv",
            "PotIns",
            "MantColectores",
            "MantSfv",
        }

        for k, v in payload.items():
            if k in allowed_fields and hasattr(d, k):
                setattr(d, k, v)
            else:
                # Ignoramos silenciosamente claves fuera de allowed_fields
                log.debug("DivisionSistemas.update: ignorando campo no permitido %r", k)

        now = _now()
        if hasattr(d, "UpdatedAt"):
            d.UpdatedAt = now
        if hasattr(d, "Version"):
            d.Version = (d.Version or 0) + 1
        if user and hasattr(d, "ModifiedBy"):
            d.ModifiedBy = user

        db.commit()
        db.refresh(d)
        return d

    # ------------------------------------------------------------------ #
    # Catálogos para combos en la UI
    # ------------------------------------------------------------------ #
    def catalogs(self, db: Session) -> Dict[str, Any]:
        """
        Devuelve todos los catálogos que necesita el front para armar el mantenedor:

        - tiposLuminarias
        - tiposEquiposCalefaccion (mismo catálogo para calefacción, refrigeración y ACS;
          en el front se puede filtrar por código si lo necesitan: CAL / FR / ACS, etc.)
        - energeticos
        - tiposColectores
        - compatibilidadesEquiposEnergeticos: lista de relaciones Equipo ↔ Energético
        """
        # Luminarias
        luminarias: List[TipoLuminaria] = (
            db.query(TipoLuminaria)
            .order_by(TipoLuminaria.Nombre, TipoLuminaria.Id)
            .all()
        )

        # Equipos de calefacción/refrigeración/ACS (el mismo catálogo)
        equipos: List[TipoEquipoCalefaccion] = (
            db.query(TipoEquipoCalefaccion)
            .order_by(TipoEquipoCalefaccion.Nombre, TipoEquipoCalefaccion.Id)
            .all()
        )

        # Energéticos
        energeticos: List[Energetico] = (
            db.query(Energetico)
            .order_by(Energetico.Nombre, Energetico.Id)
            .all()
        )

        # Colectores (ACS)
        colectores: List[TipoColector] = (
            db.query(TipoColector)
            .order_by(TipoColector.Nombre, TipoColector.Id)
            .all()
        )

        # Relación Equipo ↔ Energético
        rels: List[TipoEquipoCalefaccionEnergetico] = (
            db.query(TipoEquipoCalefaccionEnergetico)
            .order_by(
                TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId,
                TipoEquipoCalefaccionEnergetico.EnergeticoId,
            )
            .all()
        )

        def _simple(obj: Any, extra_fields: Optional[List[str]] = None) -> Dict[str, Any]:
            """
            Convierte una entidad simple en un dict con al menos Id, Nombre, Active (si existe).
            `extra_fields` permite agregar columnas opcionales como Codigo/Tipo.
            """
            data: Dict[str, Any] = {
                "Id": getattr(obj, "Id", None),
                "Nombre": getattr(obj, "Nombre", None),
            }
            if hasattr(obj, "Active"):
                data["Active"] = getattr(obj, "Active", None)
            if extra_fields:
                for f in extra_fields:
                    if hasattr(obj, f):
                        data[f] = getattr(obj, f)
            return data

        return {
            "tiposLuminarias": [_simple(l) for l in luminarias],
            "tiposEquiposCalefaccion": [
                # Si tu modelo tiene columna Codigo/Tipo/FR/ACS, la exponemos:
                _simple(e, extra_fields=["Codigo", "Tipo"])
                for e in equipos
            ],
            "energeticos": [_simple(en) for en in energeticos],
            "tiposColectores": [_simple(c) for c in colectores],
            "compatibilidadesEquiposEnergeticos": [
                {
                    "Id": r.Id,
                    "TipoEquipoCalefaccionId": r.TipoEquipoCalefaccionId,
                    "EnergeticoId": r.EnergeticoId,
                }
                for r in rels
            ],
        }
