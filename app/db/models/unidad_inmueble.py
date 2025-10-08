from __future__ import annotations
from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class UnidadInmueble(Base):
    __tablename__ = "UnidadesInmuebles"   # <- PLURAL/PLURAL CONSISTENTE
    __table_args__ = {"schema": "dbo"}

    InmuebleId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.Divisiones.Id", ondelete="RESTRICT"), primary_key=True
    )
    UnidadId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.Unidades.Id", ondelete="RESTRICT"), primary_key=True
    )
