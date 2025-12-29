from __future__ import annotations

from sqlalchemy import Column, Integer, String
from app.db.base_class import Base  # ajusta si tu Base está en otro path


class TipoUso(Base):
    __tablename__ = "TipoUsos"
    __table_args__ = {"schema": "dbo"}

    Id = Column(Integer, primary_key=True, index=True)
    Nombre = Column(String, nullable=True)
