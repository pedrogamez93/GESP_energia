# app/services/sistemas_mantenedores_service.py
from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.db.models.tipo_equipo_calefaccion_energetico import TipoEquipoCalefaccionEnergetico
from app.db.models.energetico import Energetico
from app.db.models.tipo_colector import TipoColector


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
    @staticmethod
    def _payload(data: Any) -> Dict[str, Any]:
        """Helper para normalizar payloads (Pydantic o dict)"""
        if hasattr(data, "model_dump"):
            return data.model_dump(exclude_unset=True)
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v is not None}
        return {}

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
        p = self._payload(data)

        eq = TipoEquipoCalefaccion()
        eq.Nombre = p["nombre"]

        if hasattr(eq, "Codigo"):
            eq.Codigo = p.get("codigo")
        if hasattr(eq, "Active"):
            eq.Active = p.get("active", True)

        # Clasificación: este mantenedor es de Refrigeración
        if hasattr(eq, "AC"):
            eq.AC = bool(p.get("AC", False))
        if hasattr(eq, "CA"):
            eq.CA = bool(p.get("CA", False))
        if hasattr(eq, "FR"):
            # siempre debe quedar FR = True (aunque el front no lo mande)
            eq.FR = bool(p.get("FR", True)) or True

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
        p = self._payload(data)

        if "nombre" in p:
            eq.Nombre = p["nombre"]
        if "codigo" in p and hasattr(eq, "Codigo"):
            eq.Codigo = p["codigo"]
        if "active" in p and hasattr(eq, "Active"):
            eq.Active = p["active"]

        # Actualizar clasificación si viene
        if hasattr(eq, "AC") and "AC" in p:
            eq.AC = bool(p["AC"])
        if hasattr(eq, "CA") and "CA" in p:
            eq.CA = bool(p["CA"])
        if hasattr(eq, "FR") and "FR" in p:
            # nunca permitimos desmarcar FR desde este mantenedor
            eq.FR = bool(p["FR"]) or True
        elif hasattr(eq, "FR"):
            # si no vino, igual lo dejamos True
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
        p = self._payload(data)

        eq = TipoEquipoCalefaccion()
        eq.Nombre = p["nombre"]

        if hasattr(eq, "Codigo"):
            eq.Codigo = p.get("codigo")
        if hasattr(eq, "Active"):
            eq.Active = p.get("active", True)

        # Clasificación: este mantenedor es de ACS
        if hasattr(eq, "AC"):
            eq.AC = bool(p.get("AC", True)) or True
        if hasattr(eq, "CA"):
            eq.CA = bool(p.get("CA", False))
        if hasattr(eq, "FR"):
            eq.FR = bool(p.get("FR", False))

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
        p = self._payload(data)

        if "nombre" in p:
            eq.Nombre = p["nombre"]
        if "codigo" in p and hasattr(eq, "Codigo"):
            eq.Codigo = p["codigo"]
        if "active" in p and hasattr(eq, "Active"):
            eq.Active = p["active"]

        if hasattr(eq, "AC") and "AC" in p:
            eq.AC = bool(p["AC"]) or True
        elif hasattr(eq, "AC"):
            eq.AC = True  # siempre ACS

        if hasattr(eq, "CA") and "CA" in p:
            eq.CA = bool(p["CA"])
        if hasattr(eq, "FR") and "FR" in p:
            eq.FR = bool(p["FR"])

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
