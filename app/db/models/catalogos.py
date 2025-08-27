# app/db/models/catalogos.py
from __future__ import annotations
from sqlalchemy import BigInteger, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TipoUnidad(Base):
    __tablename__ = "TipoUnidades"
    __table_args__ = {"schema": "dbo"}
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)
    OldId: Mapped[int | None] = mapped_column(BigInteger)

class TipoPropiedad(Base):
    __tablename__ = "TipoPropiedades"
    __table_args__ = {"schema": "dbo"}
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)
    Orden: Mapped[int | None] = mapped_column(Integer)

class TipoUso(Base):
    __tablename__ = "TipoUsos"
    __table_args__ = {"schema": "dbo"}
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)
