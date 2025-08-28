from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Integer, Boolean, DateTime, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class PlanGestionTarea(Base):
    __tablename__ = "PlanGestion_Tareas"
    __table_args__ = {"schema": "dbo"}

    # PK
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Metadatos / estado
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False)

    ModifiedBy: Mapped[str | None] = mapped_column(Text, nullable=True)   # nvarchar(max)
    CreatedBy:  Mapped[str | None] = mapped_column(Text, nullable=True)   # nvarchar(max)

    # FKs
    DimensionBrechaId: Mapped[int] = mapped_column(BigInteger, ForeignKey("dbo.DimensionBrechas.Id"), nullable=False)
    AccionId:          Mapped[int] = mapped_column(BigInteger, ForeignKey("dbo.Acciones.Id"), nullable=False)

    # Datos de la tarea
    Nombre:         Mapped[str]              = mapped_column(String(200), nullable=False)
    FechaInicio:    Mapped[datetime]         = mapped_column(DateTime, nullable=False)
    FechaFin:       Mapped[datetime]         = mapped_column(DateTime, nullable=False)
    Responsable:    Mapped[str]              = mapped_column(String(100), nullable=False)
    EstadoAvance:   Mapped[str]              = mapped_column(String(50),  nullable=False)
    Observaciones:  Mapped[str | None]       = mapped_column(String(500), nullable=True)
