# app/services/unidades_areas_service.py
from __future__ import annotations
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db.models.unidad import Unidad
from app.db.models.area import Area  # asumiendo que existe app.db.models.area.Area


class UnidadesAreasService:
    """
    Maneja la relación Unidad ⇄ Área con exclusividad por Área:
    - Cada Área solo puede tener una (1) Unidad.
    - Una Unidad puede estar en muchas Áreas (si así lo deseas).
    """

    def __init__(self, db: Session):
        self.db = db

    def _check_exists(self, model, id_: int, not_found_msg: str) -> None:
        if not self.db.query(model).filter(model.Id == id_).first():
            raise HTTPException(status_code=404, detail=not_found_msg)

    def get_unidad_by_area(self, area_id: int) -> Optional[int]:
        """
        Devuelve el Id de la Unidad asignada al Área (o None si no hay).
        """
        row = self.db.execute(
            text("""
                SELECT TOP 1 ua.UnidadId
                FROM dbo.UnidadesAreas ua WITH (NOLOCK)
                WHERE ua.AreaId = :area_id
            """),
            {"area_id": area_id},
        ).first()
        return int(row[0]) if row else None

    def assign_exclusive(self, area_id: int, unidad_id: int) -> dict:
        """
        Asigna unidad_id al área_id de forma EXCLUSIVA:
        - Borra cualquier asignación previa del área.
        - Inserta (unidad_id, area_id) si no estaba ya igual.
        Respuesta indica si fue 'created', 'reassigned' o 'noop'.
        """
        self._check_exists(Area, area_id, "Área no encontrada")
        self._check_exists(Unidad, unidad_id, "Unidad no encontrada")

        current = self.get_unidad_by_area(area_id)

        # Idempotencia: ya está asignada a esa misma unidad
        if current == unidad_id:
            return {"area_id": area_id, "unidad_id": unidad_id, "status": "noop"}

        # Borrar cualquiera anterior (exclusividad por área)
        self.db.execute(
            text("""
                DELETE FROM dbo.UnidadesAreas
                WHERE AreaId = :area_id
            """),
            {"area_id": area_id},
        )

        # Insertar la nueva
        self.db.execute(
            text("""
                INSERT INTO dbo.UnidadesAreas (UnidadId, AreaId)
                VALUES (:unidad_id, :area_id)
            """),
            {"unidad_id": unidad_id, "area_id": area_id},
        )
        self.db.commit()

        return {
            "area_id": area_id,
            "unidad_id": unidad_id,
            "status": "created" if current is None else "reassigned",
            "previous_unidad_id": current,
        }

    def unassign(self, area_id: int) -> dict:
        """
        Quita la Unidad del Área (si existe). Es idempotente.
        """
        self._check_exists(Area, area_id, "Área no encontrada")

        current = self.get_unidad_by_area(area_id)
        if current is None:
            return {"area_id": area_id, "status": "noop"}

        self.db.execute(
            text("""
                DELETE FROM dbo.UnidadesAreas
                WHERE AreaId = :area_id
            """),
            {"area_id": area_id},
        )
        self.db.commit()
        return {"area_id": area_id, "status": "deleted", "previous_unidad_id": current}

    def assign_bulk_to_unidad(self, unidad_id: int, areas: list[int]) -> dict:
        """
        Asigna EXCLUSIVAMENTE una misma Unidad a varias Áreas (bulk):
        - Cada área queda con 'unidad_id', reemplazando la que tuviera antes.
        - Resumen: created / reassigned / not_found (áreas inexistentes).
        """
        self._check_exists(Unidad, unidad_id, "Unidad no encontrada")

        areas = list({int(a) for a in (areas or []) if a})
        if not areas:
            return {"created": [], "reassigned": [], "not_found": []}

        # Verificar cuáles áreas existen
        rows = self.db.execute(
            text("SELECT Id FROM dbo.Areas WITH (NOLOCK) WHERE Id IN :ids")
            .bindparams(),
            {"ids": tuple(areas)},
        ).all()
        existentes = {int(r[0]) for r in rows}
        not_found = [a for a in areas if a not in existentes]

        created, reassigned = [], []
        for area_id in existentes:
            prev = self.get_unidad_by_area(area_id)
            if prev == unidad_id:
                continue  # noop

            # exclusividad: borrar lo anterior
            self.db.execute(
                text("DELETE FROM dbo.UnidadesAreas WHERE AreaId = :area_id"),
                {"area_id": area_id},
            )
            # insertar nuevo vínculo
            self.db.execute(
                text("INSERT INTO dbo.UnidadesAreas (UnidadId, AreaId) VALUES (:uid,:aid)"),
                {"uid": unidad_id, "aid": area_id},
            )
            if prev is None:
                created.append(area_id)
            else:
                reassigned.append(area_id)

        self.db.commit()
        return {"created": created, "reassigned": reassigned, "not_found": not_found}
