from __future__ import annotations

from sqlalchemy import String, BigInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UsuarioInstitucion(Base):
    __tablename__ = "UsuariosInstituciones"
    __table_args__ = (
        # Índices útiles para búsquedas por usuario o por institución
        Index("IX_UsuariosInstituciones_UsuarioId", "UsuarioId"),
        Index("IX_UsuariosInstituciones_InstitucionId", "InstitucionId"),
        {"schema": "dbo"},
    )

    # Clave compuesta
    UsuarioId: Mapped[str] = mapped_column(
        String(450),
        ForeignKey("dbo.AspNetUsers.Id", ondelete="CASCADE"),
        primary_key=True,
    )
    InstitucionId: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("dbo.Instituciones.Id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relación inversa a Institucion (coincide con institucion.py)
    InstitucionObj: Mapped["Institucion"] = relationship(
        "Institucion",
        back_populates="UsuariosInstituciones",
        lazy="joined",
    )

    # (Opcional) Si quieres la relación al usuario Identity:
    # UserObj: Mapped["AspNetUser"] = relationship("AspNetUser", lazy="joined")

    def __repr__(self) -> str:  # útil para debug
        return f"UsuarioInstitucion(UsuarioId={self.UsuarioId!r}, InstitucionId={self.InstitucionId!r})"
