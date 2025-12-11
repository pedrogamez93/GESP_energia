# app/api/v1/sistemas_mantenedores.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# 👇 Usa exactamente las mismas dependencias que usas en otros routers
from app.db.session  import get_db, get_current_active_user

from app.services.division_sistemas_service import DivisionSistemasService

router = APIRouter(tags=["Sistemas - Mantenedores"])

svc = DivisionSistemasService()


@router.get("/sistemas/refrigeracion/catalogos")
def get_refrigeracion_catalogos(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Catálogos para el mantenedor de Sistema de Refrigeración.
    """
    return svc.refrigeracion_catalogos(db)


@router.get("/sistemas/acs/catalogos")
def get_acs_catalogos(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Catálogos para el mantenedor de Agua Caliente Sanitaria (ACS).
    """
    return svc.acs_catalogos(db)
