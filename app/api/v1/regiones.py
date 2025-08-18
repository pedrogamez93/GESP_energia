# app/api/v1/regiones.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.comuna import Region
from app.schemas.region import RegionDTO

router = APIRouter()

@router.get("/regiones", response_model=list[RegionDTO])
def get_regiones(db: Session = Depends(get_db)):
    # Igual que en .NET: order by Posicion
    regs = db.query(Region).order_by(Region.Posicion).all()
    return regs