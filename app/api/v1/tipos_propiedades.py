from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.db.models.tipo_propiedad import TipoPropiedad
from app.schemas.tipo_propiedad import TipoPropiedadDTO

router = APIRouter(prefix="/api/v1/tipo-propiedades", tags=["Catálogos"])


@router.get("", response_model=List[TipoPropiedadDTO])
def list_tipo_propiedades(db: Session = Depends(get_db)):
    rows = (
        db.query(TipoPropiedad)
        .order_by(TipoPropiedad.Orden, TipoPropiedad.Id)
        .all()
    )
    return rows
