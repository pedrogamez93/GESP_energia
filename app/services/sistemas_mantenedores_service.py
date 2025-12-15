# app/services/sistemas_mantenedores_service.py
from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.db.models.tipo_equipo_calefaccion_energetico import TipoEquipoCalefaccionEnergetico
from app.db.models.energetico import Energetico
from app.db.models.tipos_colectores import TipoColector


class SistemasMantenedoresService:
    """
    Lógica para los mantenedores de:
    - Sistema de Refrigeración
    - Agua Caliente Sanitaria (ACS)
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------
    def _get_tipo_equipo(self, tipo_equipo_id: int) -> TipoEquipoCalefaccion:
        obj = self.db.get(TipoEquipoCalefaccion, tipo_equipo_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Tipo de equipo no encontrado")
        return obj

    def _get_rel(self, rel_id: int) -> TipoEquipoCalefaccionEnergetico:
        obj = self.db.get(TipoEquipoCalefaccionEnergetico, rel_id)
        if not obj:
            raise HTTPException(
                status_code=404,
                detail="Compatibilidad equipo-energético no encontrada",
            )
        return obj

    # ------------------------------------------------------------------
    # Catálogos de lectura
    # ------------------------------------------------------------------
    def catalogos_refrigeracion(self) -> Dict[str, Any]:
        """
        Devuelve:
        - equipos con flag FR = true
        - todos los energéticos
        - compatibilidades equipo↔energético
        - temperaturas fijas [22, 23, 24]
        """
        equipos = (
            self.db.query(TipoEquipoCalefaccion)
            .filter(getattr(TipoEquipoCalefaccion, "FR") == True)  # noqa: E712
            .order_by(TipoEquipoCalefaccion.Nombre)
            .all()
        )

        energeticos = (
            self.db.query(Energetico)
            .order_by(Energetico.Nombre)
            .all()
        )

        compat = (
            self.db.query(TipoEquipoCalefaccionEnergetico)
            .order_by(
                TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId,
                TipoEquipoCalefaccionEnergetico.EnergeticoId,
            )
            .all()
        )

        return {
            "equipos": equipos,
            "energeticos": energeticos,
            "compatibilidades": compat,
            "temperaturas": [22, 23, 24],
        }

    def catalogos_acs(self) -> Dict[str, Any]:
        """
        Devuelve:
        - equipos con flag AC = true
        - todos los energéticos
        - compatibilidades equipo↔energético
        - colectores solares
        """
        equipos = (
            self.db.query(TipoEquipoCalefaccion)
            .filter(getattr(TipoEquipoCalefaccion, "AC") == True)  # noqa: E712
            .order_by(TipoEquipoCalefaccion.Nombre)
            .all()
        )

        energeticos = (
            self.db.query(Energetico)
            .order_by(Energetico.Nombre)
            .all()
        )

        compat = (
            self.db.query(TipoEquipoCalefaccionEnergetico)
            .order_by(
                TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId,
                TipoEquipoCalefaccionEnergetico.EnergeticoId,
            )
            .all()
        )

        colectores = (
            self.db.query(TipoColector)
            .order_by(TipoColector.Nombre)
            .all()
        )

        return {
            "equipos": equipos,
            "energeticos": energeticos,
            "compatibilidades": compat,
            "colectores": colectores,
        }

    # ------------------------------------------------------------------
    # CRUD Equipos Refrigeración
    # ------------------------------------------------------------------
    def crear_equipo_refrigeracion(self, data: Dict[str, Any]) -> TipoEquipoCalefaccion:
        eq = TipoEquipoCalefaccion()
        eq.Nombre = data["nombre"]
        if hasattr(eq, "Codigo"):
            eq.Codigo = data.get("codigo")
        if hasattr(eq, "Active"):
            eq.Active = data.get("active", True)
        if hasattr(eq, "FR"):
            eq.FR = True  # marcamos como equipo de Refrigeración
        self.db.add(eq)
        self.db.commit()
        self.db.refresh(eq)
        return eq

    def actualizar_equipo_refrigeracion(
        self,
        tipo_equipo_id: int,
        data: Dict[str, Any],
    ) -> TipoEquipoCalefaccion:
        eq = self._get_tipo_equipo(tipo_equipo_id)

        if "nombre" in data:
            eq.Nombre = data["nombre"]
        if "codigo" in data and hasattr(eq, "Codigo"):
            eq.Codigo = data["codigo"]
        if "active" in data and hasattr(eq, "Active"):
            eq.Active = data["active"]

        if hasattr(eq, "FR") and not getattr(eq, "FR", False):
            eq.FR = True

        self.db.commit()
        self.db.refresh(eq)
        return eq

    def eliminar_equipo_refrigeracion(self, tipo_equipo_id: int) -> None:
        eq = self._get_tipo_equipo(tipo_equipo_id)
        self.db.delete(eq)
        self.db.commit()

    # ------------------------------------------------------------------
    # CRUD Equipos ACS
    # ------------------------------------------------------------------
    def crear_equipo_acs(self, data: Dict[str, Any]) -> TipoEquipoCalefaccion:
        eq = TipoEquipoCalefaccion()
        eq.Nombre = data["nombre"]
        if hasattr(eq, "Codigo"):
            eq.Codigo = data.get("codigo")
        if hasattr(eq, "Active"):
            eq.Active = data.get("active", True)
        if hasattr(eq, "AC"):
            eq.AC = True  # marcamos como equipo de ACS
        self.db.add(eq)
        self.db.commit()
        self.db.refresh(eq)
        return eq

    def actualizar_equipo_acs(
        self,
        tipo_equipo_id: int,
        data: Dict[str, Any],
    ) -> TipoEquipoCalefaccion:
        eq = self._get_tipo_equipo(tipo_equipo_id)

        if "nombre" in data:
            eq.Nombre = data["nombre"]
        if "codigo" in data and hasattr(eq, "Codigo"):
            eq.Codigo = data["codigo"]
        if "active" in data and hasattr(eq, "Active"):
            eq.Active = data["active"]

        if hasattr(eq, "AC") and not getattr(eq, "AC", False):
            eq.AC = True

        self.db.commit()
        self.db.refresh(eq)
        return eq

    def eliminar_equipo_acs(self, tipo_equipo_id: int) -> None:
        eq = self._get_tipo_equipo(tipo_equipo_id)
        self.db.delete(eq)
        self.db.commit()

    # ------------------------------------------------------------------
    # CRUD Compatibilidades equipo ↔ energético
    # ------------------------------------------------------------------
    def crear_compatibilidad(
        self,
        data: Dict[str, Any],
    ) -> TipoEquipoCalefaccionEnergetico:
        rel = TipoEquipoCalefaccionEnergetico()
        rel.TipoEquipoCalefaccionId = data["tipo_equipo_calefaccion_id"]
        rel.EnergeticoId = data["energetico_id"]
        self.db.add(rel)
        self.db.commit()
        self.db.refresh(rel)
        return rel

    def eliminar_compatibilidad(self, rel_id: int) -> None:
        rel = self._get_rel(rel_id)
        self.db.delete(rel)
        self.db.commit()
