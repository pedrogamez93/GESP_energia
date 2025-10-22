# app/services/piso_units_service.py
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, insert, delete, and_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.db.models.piso import Piso
from app.db.models.unidad import Unidad
from app.db.models.unidades_pisos import UnidadesPisos


def _assert_piso_exists(db: Session, piso_id: int):
    if not db.query(Piso.Id).filter(Piso.Id == piso_id).first():
        raise HTTPException(status_code=404, detail="Piso no encontrado")


def link_unidades_to_piso(db: Session, piso_id: int, unidad_ids: List[int]) -> int:
    """
    Vincula varias Unidades a un Piso.
    Inserta solo las que no existan (idempotente).
    """
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
            db.rollback()  # por si hay error de PK/FK
    db.commit()
    return added


def list_unidades_of_piso(db: Session, piso_id: int, include_inactive: bool = True) -> List[Dict[str, Any]]:
    """
    Devuelve el detalle de todas las Unidades vinculadas a un Piso.
    """
    _assert_piso_exists(db, piso_id)

    q = (
        select(Unidad)
        .join(UnidadesPisos, UnidadesPisos.c.UnidadId == Unidad.Id)
        .where(UnidadesPisos.c.PisoId == piso_id)
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


def unlink_unidad_from_piso(db: Session, piso_id: int, unidad_id: int) -> int:
    """
    Elimina la relación entre una Unidad y un Piso.
    """
    _assert_piso_exists(db, piso_id)
    res = db.execute(
        delete(UnidadesPisos).where(
            and_(UnidadesPisos.c.PisoId == piso_id, UnidadesPisos.c.UnidadId == unidad_id)
        )
    )
    db.commit()
    return res.rowcount or 0
