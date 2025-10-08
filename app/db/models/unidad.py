# app/db/models/unidad.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger
from app.db.base import Base

class Unidad(Base):
    __tablename__ = "Unidades"
    __table_args__ = {"schema": "dbo"}
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
