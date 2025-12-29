from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.db.models.tipo_uso import TipoUso
from app.schemas.tipo_uso import TipoUsoDTO

router = APIRouter(prefix="/api/v1/tipos-uso", tags=["Tipos de uso"])


@router.get("", response_model=List[TipoUsoDTO], summary="Listado de tipos de uso")
def list_tipos_uso(
    db: Session = Depends(get_db),
    _u: UserPublic = Depends(require_roles("ADMINISTRADOR")),
):
    return (
        db.query(TipoUso)
        .order_by(TipoUso.Id)
        .all()
    )
