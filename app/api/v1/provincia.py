from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.provincia_service import ProvinciaService
from app.schemas.provincia import ProvinciaDTO

router = APIRouter(prefix="/api/provincia", tags=["Provincia"])

@router.get("/", response_model=List[ProvinciaDTO])
def get_provincias(db: Session = Depends(get_db)):
    return ProvinciaService(db).all()

@router.get("/getByRegionId/{regionId}", response_model=List[ProvinciaDTO])
def get_by_region_id(regionId: int, db: Session = Depends(get_db)):
    provincias = ProvinciaService(db).get_by_region_id(regionId)
    if not provincias:
        raise HTTPException(status_code=404, detail="Provincias no encontradas")
    return provincias
