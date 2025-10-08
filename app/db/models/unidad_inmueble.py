from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UnidadInmueble(Base):
    """
    Tabla puente entre Divisiones (inmuebles) y Unidades.
    En BD se llama dbo.UnidadesInmuebles (plural/plural).
    """
    __tablename__ = "UnidadesInmuebles"
    __table_args__ = (
        {"schema": "dbo"},
        # Evita duplicados y favorece búsquedas
        UniqueConstraint("InmuebleId", "UnidadId", name="uq_UnidadesInmuebles_Inmueble_Unidad"),
        Index("ix_UnidadesInmuebles_InmuebleId", "InmuebleId"),
        Index("ix_UnidadesInmuebles_UnidadId", "UnidadId"),
    )

    # IMPORTANTE:
    # En esta base, "inmueble" está modelado en dbo.Divisiones.
    InmuebleId: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("dbo.Divisiones.Id", ondelete="RESTRICT"),
        primary_key=True,
    )

    UnidadId: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("dbo.Unidades.Id", ondelete="RESTRICT"),
        primary_key=True,
    )

    def __repr__(self) -> str:  # útil para logs/debug
        return f"<UnidadInmueble InmuebleId={self.InmuebleId} UnidadId={self.UnidadId}>"
