# app/services/sistemas_mantenedores_service.py
from __future__ import annotations

from typing import Any, Dict, List
from sqlalchemy.orm import Session

from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.db.models.tipo_equipo_calefaccion_energetico import (
    TipoEquipoCalefaccionEnergetico,
)
from app.db.models.energetico import Energetico
from app.db.models.tipos_colectores import TipoColector


class SistemasMantenedoresService:
    """
    Catálogos globales para los mantenedores de:
    - Sistema de Refrigeración
    - Agua Caliente Sanitaria (ACS)

    **OJO**: aquí NO se toca Division ni se usan los campos
    EquipoRefrigeracionId / EquipoAcsId, etc. Son sólo catálogos.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ----------------- REFRIGERACIÓN ----------------- #
    def catalogos_refrigeracion(self) -> Dict[str, Any]:
        """
        Devuelve:
        - equiposRefrigeracion: lista de equipos marcados como FR (si existe el flag),
          si no existe el flag, devuelve todos.
        - energeticos: catálogo completo de energéticos.
        - compatibilidades: relaciones Equipo↔Energético (sólo para equipos FR si el flag existe).
        - temperaturasSeteo: lista fija [22, 23, 24].
        """

        # Intentamos filtrar por flag FR si existe en el modelo
        flag_fr = getattr(TipoEquipoCalefaccion, "FR", None)
        q_equipos = self.db.query(TipoEquipoCalefaccion)
        if flag_fr is not None:
            q_equipos = q_equipos.filter(flag_fr == True)  # noqa: E712

        equipos: List[TipoEquipoCalefaccion] = (
            q_equipos.order_by(TipoEquipoCalefaccion.Nombre, TipoEquipoCalefaccion.Id).all()
        )

        # Energéticos completos (si quieres luego filtras en front)
        energeticos: List[Energetico] = (
            self.db.query(Energetico)
            .order_by(Energetico.Nombre, Energetico.Id)
            .all()
        )

        # Compatibilidades Equipo↔Energético
        q_rels = (
            self.db.query(TipoEquipoCalefaccionEnergetico)
            .join(
                TipoEquipoCalefaccion,
                TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId
                == TipoEquipoCalefaccion.Id,
            )
        )
        if flag_fr is not None:
            q_rels = q_rels.filter(flag_fr == True)  # noqa: E712

        rels: List[TipoEquipoCalefaccionEnergetico] = q_rels.all()

        return {
            "equiposRefrigeracion": equipos,
            "energeticos": energeticos,
            "compatibilidades": rels,
            "temperaturasSeteo": [22, 23, 24],
        }

    # ----------------- ACS ----------------- #
    def catalogos_acs(self) -> Dict[str, Any]:
        """
        Devuelve:
        - equiposAcs: lista de equipos marcados como AC (si existe el flag),
          si no existe el flag, devuelve todos.
        - energeticos: catálogo completo de energéticos.
        - compatibilidades: relaciones Equipo↔Energético (sólo equipos AC si el flag existe).
        - tiposColectores: catálogo de tipos de colectores.
        """

        flag_ac = getattr(TipoEquipoCalefaccion, "AC", None)
        q_equipos = self.db.query(TipoEquipoCalefaccion)
        if flag_ac is not None:
            q_equipos = q_equipos.filter(flag_ac == True)  # noqa: E712

        equipos: List[TipoEquipoCalefaccion] = (
            q_equipos.order_by(TipoEquipoCalefaccion.Nombre, TipoEquipoCalefaccion.Id).all()
        )

        energeticos: List[Energetico] = (
            self.db.query(Energetico)
            .order_by(Energetico.Nombre, Energetico.Id)
            .all()
        )

        q_rels = (
            self.db.query(TipoEquipoCalefaccionEnergetico)
            .join(
                TipoEquipoCalefaccion,
                TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId
                == TipoEquipoCalefaccion.Id,
            )
        )
        if flag_ac is not None:
            q_rels = q_rels.filter(flag_ac == True)  # noqa: E712

        rels: List[TipoEquipoCalefaccionEnergetico] = q_rels.all()

        colectores: List[TipoColector] = (
            self.db.query(TipoColector)
            .order_by(TipoColector.Nombre, TipoColector.Id)
            .all()
        )

        return {
            "equiposAcs": equipos,
            "energeticos": energeticos,
            "compatibilidades": rels,
            "tiposColectores": colectores,
        }
