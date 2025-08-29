from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import Boolean, Integer, BigInteger, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Institucion(Base):
    __tablename__ = "Instituciones"
    __table_args__ = {"schema": "dbo"}

    # Alineado con SQL Server (BIGINT)
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    UpdatedAt: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    Version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    Active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    ModifiedBy: Mapped[str | None] = mapped_column(String(450), nullable=True)
    CreatedBy:  Mapped[str | None] = mapped_column(String(450), nullable=True)

    Nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    OldId:  Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relación a la tabla de vínculo (declarada en otro módulo)
    UsuariosInstituciones: Mapped[List["UsuarioInstitucion"]] = relationship(
        "UsuarioInstitucion",
        back_populates="InstitucionObj",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
