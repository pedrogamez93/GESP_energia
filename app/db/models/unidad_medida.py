# app/db/models/unidad_medida.py
from __future__ import annotations
from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class UnidadMedida(Base):
    __tablename__ = "UnidadesMedida"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)
    # <-- NUEVO: columna ya existe en SQL (dbo.UnidadesMedida.Abrv)
    Abrv: Mapped[str | None] = mapped_column(Text)
