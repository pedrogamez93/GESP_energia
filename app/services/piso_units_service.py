from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, insert, delete, and_
from sqlalchemy.exc import IntegrityError

from app.db.models.piso import Piso
from app.db.models.unidad import Unidad
from app.db.models.unidades_pisos import UnidadesPisos

def _assert_piso_exists(db: Session, piso_id: int):
    if not db.query(Piso.Id).filter(Piso.Id == piso_id).first():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Piso no encontrado")

def link_unidades_to_piso(db: Session, piso_id: int, unidad_ids: List[int]) -> int:
    _assert_piso_exists(db, piso_id)
    added = 0
    for uid in unidad_ids:
        exists = db.execute(
            select(UnidadesPisos.c.UnidadId).where(
                and_(UnidadesPisos.c.UnidadId == uid, UnidadesPisos.c.PisoId == piso_id)
            )
        ).first()
        if exists:
            continue
        try:
            db.execute(insert(UnidadesPisos).values(UnidadId=uid, PisoId=piso_id))
            added += 1
        except IntegrityError:
            db.rollback()  # PK o FK; seguimos con el resto
    db.commit()
    return added

def list_unidades_of_piso(db: Session, piso_id: int, include_inactive: bool = True) -> List[Dict[str, Any]]:
    _assert_piso_exists(db, piso_id)
    # JOIN a dbo.Unidades para traer detalle
    j = (
        select(Unidad)
        .join(UnidadesPisos, UnidadesPisos.c.UnidadId == Unidad.Id)
        .where(UnidadesPisos.c.PisoId == piso_id)
    )
    if not include_inactive and hasattr(Unidad, "Active"):
        j = j.where(Unidad.Active == True)

    rows = db.execute(j).scalars().all()

    result = []
    for u in rows:
        result.append({
            "id": getattr(u, "Id"),
            "nombre": getattr(u, "Nombre", None),
            "servicio_id": getattr(u, "ServicioId", None),
            "activo": getattr(u, "Active", None),
        })
    return result

def unlink_unidad_from_piso(db: Session, piso_id: int, unidad_id: int) -> int:
    _assert_piso_exists(db, piso_id)
    res = db.execute(
        delete(UnidadesPisos).where(
            and_(UnidadesPisos.c.PisoId == piso_id, UnidadesPisos.c.UnidadId == unidad_id)
        )
    )
    db.commit()
    return res.rowcount or 0
