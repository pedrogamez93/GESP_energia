# app/db/models/institucion.py
from datetime import datetime
from sqlalchemy import Boolean, Integer, BigInteger, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Institucion(Base):
    __tablename__ = "Instituciones"
    __table_args__ = {"schema": "dbo"}  # 👈 IMPORTANTE

    # ⚠️ Alinea el tipo con tu DB real.
    # Si en SQL Server es BIGINT, usa BigInteger; si es INT, usa Integer en TODOS los lados.
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    Version:   Mapped[int]      = mapped_column(Integer,  nullable=False, default=1)
    Active:    Mapped[bool]     = mapped_column(Boolean,  nullable=False, default=True)

    ModifiedBy: Mapped[str | None] = mapped_column(String(450), nullable=True)
    CreatedBy:  Mapped[str | None] = mapped_column(String(450), nullable=True)

    Nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    OldId:  Mapped[int]        = mapped_column(Integer,     nullable=False, default=0)

    UsuariosInstituciones: Mapped[list["UsuarioInstitucion"]] = relationship(
        "UsuarioInstitucion",
        back_populates="InstitucionObj",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

class UsuarioInstitucion(Base):
    __tablename__ = "UsuariosInstituciones"
    __table_args__ = {"schema": "dbo"}  # 👈 IMPORTANTE

    UsuarioId: Mapped[str] = mapped_column(String(450), primary_key=True, index=True)

    # 👇 referencia con esquema explícito y tipo alineado con Institucion.Id
    InstitucionId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.Instituciones.Id"), primary_key=True, index=True
    )

    InstitucionObj: Mapped["Institucion"] = relationship(
        "Institucion", back_populates="UsuariosInstituciones"
    )
