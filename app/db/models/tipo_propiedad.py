from __future__ import annotations

from sqlalchemy import Column, Integer, String
from app.db.base import Base


class TipoPropiedad(Base):
    __tablename__ = "TipoPropiedades"
    __table_args__ = {"schema": "dbo"}

    Id = Column(Integer, primary_key=True, index=True)
    Nombre = Column(String, nullable=True)
    Orden = Column(Integer, nullable=True)
