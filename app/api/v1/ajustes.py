# app/api/v1/ajustes.py
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.ajustes import AjusteDTO, AjustePatchDTO
from app.services.ajuste_service import AjusteService

router = APIRouter(prefix="/api/v1/ajustes", tags=["Ajustes"])
DbDep = Annotated[Session, Depends(get_db)]

@router.get("", response_model=AjusteDTO, summary="Obtiene flags globales (AllowAnonymous)")
def get_ajustes(db: DbDep):
    obj = AjusteService(db).get()
    return AjusteDTO.model_validate(obj)

@router.patch("", response_model=AjusteDTO, summary="(ADMIN) Actualiza flags globales")
def patch_ajustes(
    data: AjustePatchDTO,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = AjusteService(db).patch(data)
    return AjusteDTO.model_validate(obj)
