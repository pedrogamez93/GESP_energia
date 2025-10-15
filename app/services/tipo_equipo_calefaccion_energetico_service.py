from __future__ import annotations
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.tipo_equipo_calefaccion_energetico import (
    TipoEquipoCalefaccionEnergetico as Compat,
)
from app.db.models.tipo_equipo_calefaccion import (
    TipoEquipoCalefaccion as Equipo,
)
from app.db.models.energetico import Energetico
from app.schemas.tipo_equipo_calefaccion_energetico import CompatIn


def list_all(db: Session):
    """Lista todas las compatibilidades equipo↔energético."""
    return db.query(Compat).all()


def _must_exist(db: Session, model, id_: int, label: str):
    obj = db.get(model, id_)
    if not obj:
        raise HTTPException(status_code=404, detail=f"{label} {id_} no existe")
    return obj


def create_compat(db: Session, payload: CompatIn):
    """
    Crea una compatibilidad entre un tipo de equipo y un energético.
    Valida existencia y evita duplicados.
    """
    _must_exist(db, Equipo, payload.TipoEquipoCalefaccionId, "TipoEquipoCalefaccion")
    _must_exist(db, Energetico, payload.EnergeticoId, "Energetico")

    exists = (
        db.query(Compat)
        .filter(
            Compat.TipoEquipoCalefaccionId == payload.TipoEquipoCalefaccionId,
            Compat.EnergeticoId == payload.EnergeticoId,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Compatibilidad ya existe")

    obj = Compat(
        TipoEquipoCalefaccionId=payload.TipoEquipoCalefaccionId,
        EnergeticoId=payload.EnergeticoId,
    )
    db.add(obj)
    db.commit()
    try:
        db.refresh(obj)
    except Exception:
        # Si la tabla no tiene Id autoincremental, refresh no es crítico
        pass
    return obj


def delete_compat(db: Session, payload: CompatIn):
    """Elimina una compatibilidad (par equipo, energético)."""
    obj = (
        db.query(Compat)
        .filter(
            Compat.TipoEquipoCalefaccionId == payload.TipoEquipoCalefaccionId,
            Compat.EnergeticoId == payload.EnergeticoId,
        )
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Compatibilidad no encontrada")
    db.delete(obj)
    db.commit()


# Útil si luego validas en PUT de sistemas:
def is_compatible(db: Session, equipo_id: int | None, energetico_id: int | None) -> bool:
    if not equipo_id or not energetico_id:
        return True
    return (
        db.query(Compat)
        .filter(
            Compat.TipoEquipoCalefaccionId == equipo_id,
            Compat.EnergeticoId == energetico_id,
        )
        .first()
        is not None
    )
