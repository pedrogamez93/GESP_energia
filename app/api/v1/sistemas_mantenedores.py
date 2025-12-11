# app/api/v1/sistemas_mantenedores.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import deps  # o desde donde saques get_db / get_current_user
from app.services.division_sistemas_service import DivisionSistemasService

router = APIRouter(tags=["Sistemas - Mantenedores"])

svc = DivisionSistemasService()


@router.get("/sistemas/refrigeracion/catalogos")
def get_refrigeracion_catalogos(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    """
    Catálogos para el mantenedor de Sistema de Refrigeración.
    """
    return svc.refrigeracion_catalogos(db)


@router.get("/sistemas/acs/catalogos")
def get_acs_catalogos(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    """
    Catálogos para el mantenedor de Agua Caliente Sanitaria (ACS).
    """
    return svc.acs_catalogos(db)
