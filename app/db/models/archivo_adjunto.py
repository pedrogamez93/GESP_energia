from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class ArchivoAdjunto(Base):
    __tablename__ = "ArchivoAdjuntos"
    __table_args__ = {"schema": "dbo"}

    Id:           Mapped[int]        = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CreatedAt:    Mapped[datetime]   = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt:    Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    Version:      Mapped[int]        = mapped_column(BigInteger, nullable=False, default=1)
    Active:       Mapped[bool]       = mapped_column(Boolean, nullable=False, default=True)

    ModifiedBy:   Mapped[str | None] = mapped_column(Text)
    CreatedBy:    Mapped[str | None] = mapped_column(Text)

    Nombre:       Mapped[str]        = mapped_column(Text, nullable=False)     # nombre original
    Descripcion:  Mapped[str | None] = mapped_column(Text)                     # opcional
    DivisionId:   Mapped[int]        = mapped_column(BigInteger, nullable=False)
    TipoArchivoId:Mapped[int]        = mapped_column(BigInteger, ForeignKey("dbo.TipoArchivos.Id"), nullable=False)
    Url:          Mapped[str]        = mapped_column(Text, nullable=False)     # ruta física (UNC o local)

    tipo = relationship("TipoArchivo", viewonly=True)
