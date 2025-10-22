from sqlalchemy.orm import Session
from sqlalchemy import select, insert, delete

from app.db.models.unidades_areas import UnidadesAreas
from app.db.models.unidad import Unidad


def link_unidades_to_area(db: Session, area_id: int, unidad_ids: list[int]) -> int:
    """
    Vincula varias unidades a un área (bulk insert).
    """
    if not unidad_ids:
        return 0

    values = [{"UnidadId": uid, "AreaId": area_id} for uid in unidad_ids]
    db.execute(insert(UnidadesAreas).prefix_with("IGNORE"), values)
    db.commit()
    return len(values)


def list_unidades_of_area(db: Session, area_id: int, include_inactive: bool = True):
    """
    Lista las unidades asociadas a un área.
    """
    stmt = (
        select(Unidad)
        .join(UnidadesAreas, UnidadesAreas.c.UnidadId == Unidad.Id)
        .where(UnidadesAreas.c.AreaId == area_id)
    )

    if not include_inactive:
        stmt = stmt.where(Unidad.Active == True)

    return db.execute(stmt).scalars().all()


def unlink_unidad_from_area(db: Session, area_id: int, unidad_id: int) -> int:
    """
    Desvincula una unidad de un área.
    """
    stmt = delete(UnidadesAreas).where(
        (UnidadesAreas.c.AreaId == area_id) & (UnidadesAreas.c.UnidadId == unidad_id)
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount
