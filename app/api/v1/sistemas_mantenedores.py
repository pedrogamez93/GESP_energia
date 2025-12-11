# app/api/v1/sistemas_mantenedores.py

from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.division_sistemas_service import DivisionSistemasService

DbDep = Annotated[Session, Depends(get_db)]

router = APIRouter(
    prefix="/api/v1/sistemas",
    tags=["Sistemas - Mantenedores"],
)

svc = DivisionSistemasService()


@router.get(
    "/refrigeracion/catalogos",
    summary="Catálogos para el mantenedor de Sistema de Refrigeración",
)
def get_refrigeracion_catalogos(
    db: DbDep,
):
    """
    Devuelve:
    - equipos de refrigeración (solo FR) con sus energéticos compatibles
    - temperaturas de seteo fijas (22, 23, 24)
    """
    return svc.refrigeracion_catalogos(db)


@router.get(
    "/acs/catalogos",
    summary="Catálogos para el mantenedor de Agua Caliente Sanitaria (ACS)",
)
def get_acs_catalogos(
    db: DbDep,
):
    """
    Devuelve:
    - equipos ACS (solo AC) con sus energéticos compatibles
    - tipos de colectores solares térmicos
    """
    return svc.acs_catalogos(db)
