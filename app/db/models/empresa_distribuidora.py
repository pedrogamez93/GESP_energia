from datetime import datetime
from sqlalchemy import BigInteger, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class EmpresaDistribuidora(Base):
    __tablename__ = "EmpresaDistribuidoras"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    Version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy: Mapped[str | None] = mapped_column(Text)

    Nombre: Mapped[str | None] = mapped_column(Text)
    EnergeticoId: Mapped[int] = mapped_column(BigInteger, ForeignKey("dbo.Energeticos.Id", ondelete="CASCADE"), nullable=False)
    OldId: Mapped[int] = mapped_column(BigInteger, nullable=False)  # default 0 en BD
    RUT: Mapped[str | None] = mapped_column(Text)

    comunas: Mapped[list["EmpresasDistribuidoraComuna"]] = relationship(
        "EmpresasDistribuidoraComuna", back_populates="empresa", cascade="all, delete-orphan"
    )

class EmpresasDistribuidoraComuna(Base):
    __tablename__ = "EmpresasDistribuidoraComunas"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    Version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy: Mapped[str | None] = mapped_column(Text)

    ComunaId: Mapped[int] = mapped_column(BigInteger, ForeignKey("dbo.Comunas.Id", ondelete="CASCADE"), nullable=False)
    EmpresaDistribuidoraId: Mapped[int] = mapped_column(BigInteger, ForeignKey("dbo.EmpresaDistribuidoras.Id", ondelete="CASCADE"), nullable=False)

    empresa: Mapped["EmpresaDistribuidora"] = relationship("EmpresaDistribuidora", back_populates="comunas")
    # relación a Comuna opcional (solo si necesitas navegarla):
    # comuna: Mapped["Comuna"] = relationship("Comuna")
