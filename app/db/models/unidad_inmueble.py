from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UnidadInmueble(Base):
    """
    Tabla puente N:M entre Unidades y Divisiones (inmuebles).
    ÚNICA definición de la tabla 'dbo.UnidadesInmuebles' para evitar el error:
    'Table ... is already defined for this MetaData instance'.
    """
    __tablename__ = "UnidadesInmuebles"
    __table_args__ = (
        PrimaryKeyConstraint("InmuebleId", "UnidadId", name="PK_UnidadesInmuebles"),
        {"schema": "dbo"},
    )

    InmuebleId: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("dbo.Divisiones.Id", ondelete="RESTRICT"),
        nullable=False,
    )
    UnidadId: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("dbo.Unidades.Id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Backref hacia Unidad (definida en app/db/models/unidad.py)
    unidad: Mapped["app.db.models.unidad.Unidad"] = relationship(
        "app.db.models.unidad.Unidad",
        back_populates="unidad_inmuebles",
    )
