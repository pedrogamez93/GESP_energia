from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.db.models.tipo_uso import TipoUso
from app.schemas.tipo_uso import TipoUsoDTO

router = APIRouter(prefix="/api/v1/tipo-usos", tags=["Catálogos"])


@router.get("", response_model=List[TipoUsoDTO])
def list_tipo_usos(db: Session = Depends(get_db)):
    rows = (
        db.query(TipoUso)
        .order_by(TipoUso.Id)
        .all()
    )
    return rows
