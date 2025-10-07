# app/db/modelss/ajuste.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Ajuste(Base):
    __tablename__ = "Ajustes"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=1)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)

    # nvarchar(max) en DDL -> no los usamos aquí (NULLables) así que no los mapeamos
    # ModifiedBy / CreatedBy los gestionaremos desde servicio si te hace falta luego.

    EditUnidadPMG:     Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    DeleteUnidadPMG:   Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ComprasServicio:   Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    CreateUnidadPMG:   Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ActiveAlcanceModule: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
