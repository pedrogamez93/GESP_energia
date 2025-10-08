from typing import List
from sqlalchemy.orm import Session
from app.db.models.provincia import Provincia
from app.schemas.provincia import ProvinciaDTO

class ProvinciaService:
    def __init__(self, db: Session):
        self.db = db

    def all(self) -> List[ProvinciaDTO]:
        provincias = self.db.query(Provincia).all()
        return [ProvinciaDTO.model_validate(p) for p in provincias]

    def get_by_region_id(self, region_id: int) -> List[ProvinciaDTO]:
        provincias = self.db.query(Provincia).filter(Provincia.RegionId == region_id).all()
        return [ProvinciaDTO.model_validate(p) for p in provincias]
