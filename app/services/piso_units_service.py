from sqlalchemy.orm import Session
from sqlalchemy import select, insert, delete

from app.db.models.unidades_pisos import UnidadesPisos
from app.db.models.unidad import Unidad


def link_unidades_to_piso(db: Session, piso_id: int, unidad_ids: list[int]) -> int:
    """
    Vincula varias unidades a un piso (bulk insert).
    """
    if not unidad_ids:
        return 0

    values = [{"UnidadId": uid, "PisoId": piso_id} for uid in unidad_ids]
    db.execute(insert(UnidadesPisos).prefix_with("IGNORE"), values)  # IGNORE evita duplicados en SQL Server
    db.commit()
    return len(values)


def list_unidades_of_piso(db: Session, piso_id: int, include_inactive: bool = True):
    """
    Lista las unidades asociadas a un piso.
    """
    stmt = (
        select(Unidad)
        .join(UnidadesPisos, UnidadesPisos.c.UnidadId == Unidad.Id)
        .where(UnidadesPisos.c.PisoId == piso_id)
    )

    if not include_inactive:
        stmt = stmt.where(Unidad.Active == True)

    return db.execute(stmt).scalars().all()


def unlink_unidad_from_piso(db: Session, piso_id: int, unidad_id: int) -> int:
    """
    Desvincula una unidad de un piso.
    """
    stmt = delete(UnidadesPisos).where(
        (UnidadesPisos.c.PisoId == piso_id) & (UnidadesPisos.c.UnidadId == unidad_id)
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount
