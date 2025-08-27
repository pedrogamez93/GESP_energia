from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.db.models.sistema import Sistema
from app.db.models.modo_operacion import ModoOperacion
from app.db.models.tipo_tecnologia import TipoTecnologia

class CatalogosEquipoService:
    def list_sistemas(self, db: Session, q: str | None = None):
        stmt = select(Sistema.Id, Sistema.Nombre)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(func.lower(Sistema.Nombre).like(func.lower(like)))
        return db.execute(stmt.order_by(Sistema.Nombre)).all()

    def list_modos(self, db: Session, q: str | None = None):
        stmt = select(ModoOperacion.Id, ModoOperacion.Nombre)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(func.lower(ModoOperacion.Nombre).like(func.lower(like)))
        return db.execute(stmt.order_by(ModoOperacion.Nombre)).all()

    def list_tipos_tecnologia(self, db: Session, q: str | None = None):
        stmt = select(TipoTecnologia.Id, TipoTecnologia.Nombre)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(func.lower(TipoTecnologia.Nombre).like(func.lower(like)))
        return db.execute(stmt.order_by(TipoTecnologia.Nombre)).all()
