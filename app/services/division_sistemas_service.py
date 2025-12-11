# app/services/division_sistemas_service.py
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models.division import Division
from app.db.models.tipo_luminaria import TipoLuminaria
from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.db.models.tipo_equipo_calefaccion_energetico import (
    TipoEquipoCalefaccionEnergetico,
)
from app.db.models.energetico import Energetico
from app.db.models.tipo_colector import TipoColector  # clase que mapea a dbo.TiposColectores
from app.services.division_service import DivisionService

log = logging.getLogger("division_sistemas")


def _now() -> datetime:
    return datetime.utcnow()


# Campos de sistemas que vamos a exponer/editar
_SYSTEM_FIELDS = {
    # Iluminación
    "TipoLuminariaId",
    # Calefacción
    "EquipoCalefaccionId",
    "EnergeticoCalefaccionId",
    "TempSeteoCalefaccionId",
    # Refrigeración
    "EquipoRefrigeracionId",
    "EnergeticoRefrigeracionId",
    "TempSeteoRefrigeracionId",
    # ACS
    "EquipoAcsId",
    "EnergeticoAcsId",
    "SistemaSolarTermico",
    "ColectorId",
    "SupColectores",
    "FotoTecho",
    "SupFotoTecho",
    # Fotovoltaico
    "InstTerSisFv",
    "SupInstTerSisFv",
    "ImpSisFv",
    "SupImptSisFv",
    "PotIns",
    # Mantenciones
    "MantColectores",
    "MantSfv",
}


class DivisionSistemasService:
    """
    Lógica del mantenedor de sistemas por División:
    - Iluminación (TipoLuminariaId)
    - Calefacción (EquipoCalefaccion*, EnergeticoCalefaccion*, TempSeteoCalefaccionId)
    - Refrigeración (EquipoRefrigeracion*, EnergeticoRefrigeracion*, TempSeteoRefrigeracionId)
    - ACS (EquipoAcs*, EnergeticoAcsId, SistemaSolarTermico, ColectorId, SupColectores,
           FotoTecho, SupFotoTecho, MantColectores)
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
    # Mapear Division -> dict compatible con DivisionSistemasDTO
    # ------------------------------------------------------------------ #
    def to_dto(self, d: Division) -> Dict[str, Any]:
        """
        Convierte la entidad Division a un dict compatible con DivisionSistemasDTO.
        Usa getattr para no romper si faltara algún campo en el modelo.
        """
        data: Dict[str, Any] = {
            "DivisionId": getattr(d, "Id", None),
        }

        for field in _SYSTEM_FIELDS:
            data[field] = getattr(d, field, None)

        data["Version"] = getattr(d, "Version", None)
        return data

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
        Actualiza solo los campos de sistemas definidos en _SYSTEM_FIELDS.
        `payload` ya viene filtrado con exclude_unset=True desde el router.
        """
        d = self.get(db, division_id)

        for k, v in payload.items():
            if k in _SYSTEM_FIELDS:
                if hasattr(d, k):
                    setattr(d, k, v)
                else:
                    log.debug(
                        "DivisionSistemas.update: campo %r permitido pero no existe en modelo Division",
                        k,
                    )
            else:
                # Ignoramos silenciosamente claves fuera de _SYSTEM_FIELDS
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

        # Equipos de calefacción/refrigeración/ACS (mismo catálogo)
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

        # Colectores (ACS / FV térmico, etc.)
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
            Convierte una entidad simple en un dict con al menos Id y Nombre.
            Si el modelo tiene Active u otros campos extra (Codigo, Tipo, etc.),
            se agregan solo si existen en el modelo (para no romper la BD).
            """
            data: Dict[str, Any] = {
                "Id": getattr(obj, "Id", None),
                "Nombre": getattr(obj, "Nombre", None),
            }

            # Active solo si existe en el modelo (evita errores si la columna no está en la tabla)
            if hasattr(obj.__class__, "Active"):
                # OJO: esto NO fuerza carga desde DB si ya vino en la query;
                # pero si el modelo no tiene columna Active, ni siquiera lo intentamos.
                data["Active"] = getattr(obj, "Active", None)

            if extra_fields:
                for f in extra_fields:
                    if hasattr(obj.__class__, f):
                        data[f] = getattr(obj, f, None)

            return data

        return {
            "tiposLuminarias": [_simple(l) for l in luminarias],
            "tiposEquiposCalefaccion": [
                # Si tu modelo tiene columna Codigo/Tipo, la exponemos:
                _simple(e, extra_fields=["Codigo", "Tipo"])
                for e in equipos
            ],
            "energeticos": [_simple(en) for en in energeticos],
            "tiposColectores": [_simple(c, extra_fields=["Tipo"]) for c in colectores],
            "compatibilidadesEquiposEnergeticos": [
                {
                    "Id": r.Id,
                    "TipoEquipoCalefaccionId": r.TipoEquipoCalefaccionId,
                    "EnergeticoId": r.EnergeticoId,
                }
                for r in rels
            ],
        }
