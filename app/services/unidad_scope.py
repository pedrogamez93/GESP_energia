# app/services/unidad_scope.py
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import HTTPException


def division_id_from_unidad(db: Session, unidad_id: int) -> int:
    """
    Resuelve DivisionId (InmuebleId) desde UnidadId usando dbo.UnidadesInmuebles.

    Regla negocio confirmada: una unidad tiene EXACTAMENTE 1 inmueble.
    Si no hay fila => 404.
    Si hubiese >1 (no debería) => 409.
    """
    rows = db.execute(
        text("""
            SELECT InmuebleId
            FROM dbo.UnidadesInmuebles
            WHERE UnidadId = :unidad_id
        """),
        {"unidad_id": int(unidad_id)},
    ).all()

    if not rows:
        raise HTTPException(status_code=404, detail="Unidad no tiene inmueble asociado (UnidadesInmuebles vacío)")

    if len(rows) > 1:
        # Tu caso dijo "NO", pero lo dejamos por seguridad diagnóstica
        raise HTTPException(
            status_code=409,
            detail={
                "code": "unidad_multiple_inmuebles",
                "msg": "La unidad tiene más de un InmuebleId asociado (no esperado)",
                "unidad_id": int(unidad_id),
                "inmueble_ids": [int(r[0]) for r in rows],
            },
        )

    return int(rows[0][0])
