# app/db/models/institucion.py
from datetime import datetime
from sqlalchemy import Boolean, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Institucion(Base):
    __tablename__ = "Instituciones"

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Defaults del lado de Python/ORM para satisfacer NOT NULL
    # (se envían en el INSERT automáticamente)
    CreatedAt: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    UpdatedAt: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    Version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    Active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Pueden ser NULL
    ModifiedBy: Mapped[str | None] = mapped_column(String(450), nullable=True)
    CreatedBy: Mapped[str | None] = mapped_column(String(450), nullable=True)

    # Datos propios
    Nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    OldId: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relación con la tabla puente
    UsuariosInstituciones: Mapped[list["UsuarioInstitucion"]] = relationship(
        "UsuarioInstitucion",
        back_populates="InstitucionObj",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class UsuarioInstitucion(Base):
    __tablename__ = "UsuariosInstituciones"

    # ASP.NET Identity suele usar NVARCHAR(450) para el Id de usuario
    UsuarioId: Mapped[str] = mapped_column(String(450), primary_key=True, index=True)
    InstitucionId: Mapped[int] = mapped_column(
        Integer, ForeignKey("Instituciones.Id"), primary_key=True, index=True
    )

    InstitucionObj: Mapped["Institucion"] = relationship(
        "Institucion", back_populates="UsuariosInstituciones"
    )
