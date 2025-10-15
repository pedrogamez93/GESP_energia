from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.schemas.tipo_equipo_calefaccion_energetico import CompatIn, CompatOut
from app.services.tipo_equipo_calefaccion_energetico_service import (
    list_all, create_compat, delete_compat
)

router = APIRouter(
    prefix="/tipo-equipo-calefaccion-energeticos",
    tags=["Compatibilidades equipo↔energético"]
)

@router.get("", response_model=list[CompatOut])
def listar(db: Session = Depends(get_db)):
    rows = list_all(db)
    return [CompatOut.model_validate(r) for r in rows]

@router.post("", response_model=CompatOut, status_code=status.HTTP_201_CREATED)
def crear(payload: CompatIn, db: Session = Depends(get_db)):
    obj = create_compat(db, payload)
    return CompatOut.model_validate(obj)

@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(payload: CompatIn, db: Session = Depends(get_db)):
    delete_compat(db, payload)
    return None
