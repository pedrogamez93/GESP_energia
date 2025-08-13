from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.comuna import Region, Comuna
from app.schemas.comuna import ComunaDTO

router = APIRouter()

@router.get("/comunas/byRegionId/{id}", response_model=list[ComunaDTO])
def get_by_region_id(id: int, db: Session = Depends(get_db)):
    region = db.query(Region).filter(Region.Id == id).first()
    if not region:
        raise HTTPException(status_code=404, detail="La región seleccionada no existe")

    comunas = (
        db.query(Comuna)
        .filter(Comuna.RegionId == id)
        .order_by(Comuna.Nombre)
        .all()
    )
    return comunas
