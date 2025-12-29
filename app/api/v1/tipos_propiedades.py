from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.db.models.tipo_propiedad import TipoPropiedad
from app.schemas.tipo_propiedad import TipoPropiedadDTO

router = APIRouter(prefix="/api/v1/tipos-propiedades", tags=["Tipos de propiedades"])


@router.get("", response_model=List[TipoPropiedadDTO], summary="Listado de tipos de propiedades")
def list_tipos_propiedades(
    db: Session = Depends(get_db),
    _u: UserPublic = Depends(require_roles("ADMINISTRADOR")),
):
    # En la tabla existe Orden; priorizamos Orden y luego Id
    return (
        db.query(TipoPropiedad)
        .order_by(TipoPropiedad.Orden, TipoPropiedad.Id)
        .all()
    )
