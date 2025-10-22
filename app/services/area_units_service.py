# app/services/area_units_service.py
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, insert, delete, and_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.db.models.area import Area
from app.db.models.unidad import Unidad
from app.db.models.unidades_areas import UnidadesAreas


def _assert_area_exists(db: Session, area_id: int):
    if not db.query(Area.Id).filter(Area.Id == area_id).first():
        raise HTTPException(status_code=404, detail="Área no encontrada")


def link_unidades_to_area(db: Session, area_id: int, unidad_ids: List[int]) -> int:
    """
    Vincula varias Unidades a un Área.
    Inserta solo las que no existan (idempotente).
    """
    _assert_area_exists(db, area_id)
    added = 0
    for uid in unidad_ids:
        exists = db.execute(
            select(UnidadesAreas.c.UnidadId).where(
                and_(UnidadesAreas.c.UnidadId == uid, UnidadesAreas.c.AreaId == area_id)
            )
        ).first()
        if exists:
            continue
        try:
            db.execute(insert(UnidadesAreas).values(UnidadId=uid, AreaId=area_id))
            added += 1
        except IntegrityError:
            db.rollback()
    db.commit()
    return added


def list_unidades_of_area(db: Session, area_id: int, include_inactive: bool = True) -> List[Dict[str, Any]]:
    """
    Devuelve el detalle de todas las Unidades vinculadas a un Área.
    """
    _assert_area_exists(db, area_id)

    q = (
        select(Unidad)
        .join(UnidadesAreas, UnidadesAreas.c.UnidadId == Unidad.Id)
        .where(UnidadesAreas.c.AreaId == area_id)
    )
    if not include_inactive and hasattr(Unidad, "Active"):
        q = q.where(Unidad.Active == True)

    rows = db.execute(q).scalars().all()

    result = []
    for u in rows:
        result.append({
            "id": getattr(u, "Id"),
            "nombre": getattr(u, "Nombre", None),
            "servicio_id": getattr(u, "ServicioId", None),
            "activo": getattr(u, "Active", None),
        })
    return result


def unlink_unidad_from_area(db: Session, area_id: int, unidad_id: int) -> int:
    """
    Elimina la relación entre una Unidad y un Área.
    """
    _assert_area_exists(db, area_id)
    res = db.execute(
        delete(UnidadesAreas).where(
            and_(UnidadesAreas.c.AreaId == area_id, UnidadesAreas.c.UnidadId == unidad_id)
        )
    )
    db.commit()
    return res.rowcount or 0
