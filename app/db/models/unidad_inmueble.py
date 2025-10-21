from __future__ import annotations
from sqlalchemy import BigInteger, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from .unidad import UnidadInmueble

class UnidadInmueble(Base):
    __tablename__ = "UnidadesInmuebles"
    __table_args__ = (
        PrimaryKeyConstraint("InmuebleId", "UnidadId", name="PK_UnidadesInmuebles"),
        {"schema": "dbo"},
    )

    InmuebleId: Mapped[int] = mapped_column(BigInteger, ForeignKey("dbo.Divisiones.Id", ondelete="RESTRICT"), nullable=False)
    UnidadId: Mapped[int] = mapped_column(BigInteger, ForeignKey("dbo.Unidades.Id", ondelete="RESTRICT"), nullable=False)

    unidad: Mapped["app.db.models.unidad.Unidad"] = relationship(
        "app.db.models.unidad.Unidad", back_populates="unidad_inmuebles"
    )
