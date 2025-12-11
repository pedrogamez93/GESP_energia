# app/api/v1/sistemas_mantenedores.py
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.sistemas_mantenedores import (
    RefrigeracionCatalogosDTO,
    ACSCatalogosDTO,
)
from app.services.sistemas_mantenedores_service import SistemasMantenedoresService


DbDep = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]

router = APIRouter(
    prefix="/api/v1/sistemas",
    tags=["Sistemas - mantenedores"],
)


@router.get(
    "/refrigeracion/catalogos",
    response_model=RefrigeracionCatalogosDTO,
    summary="Catálogos para el mantenedor de Sistema de Refrigeración",
    description=(
        "Devuelve equipos de refrigeración (catálogo base) con sus "
        "energéticos compatibles y la lista fija de temperaturas de seteo (22, 23, 24)."
    ),
)
def get_refrigeracion_catalogos(
    db: DbDep,
    current_user: CurrentAdmin,
) -> RefrigeracionCatalogosDTO:
    svc = SistemasMantenedoresService(db)
    data = svc.catalogos_refrigeracion()
    # data ya es un dict con listas de ORM; Pydantic las convierte usando from_attributes=True
    return RefrigeracionCatalogosDTO.model_validate(data)


@router.get(
    "/acs/catalogos",
    response_model=ACSCatalogosDTO,
    summary="Catálogos para el mantenedor de Agua Caliente Sanitaria (ACS)",
    description=(
        "Devuelve equipos de ACS (catálogo base) con sus energéticos compatibles "
        "y tipos de colectores solares."
    ),
)
def get_acs_catalogos(
    db: DbDep,
    current_user: CurrentAdmin,
) -> ACSCatalogosDTO:
    svc = SistemasMantenedoresService(db)
    data = svc.catalogos_acs()
    return ACSCatalogosDTO.model_validate(data)
