from __future__ import annotations
from sqlalchemy import BigInteger, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TipoArchivo(Base):
    __tablename__ = "TipoArchivos"
    __table_args__ = {"schema": "dbo"}

    Id:            Mapped[int]  = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre:        Mapped[str]  = mapped_column(Text, nullable=False)
    MimeType:      Mapped[str]  = mapped_column(Text, nullable=False)
    Extension:     Mapped[str]  = mapped_column(Text, nullable=False)  # ".pdf", ".xlsx", ...
    NombreCorto:   Mapped[str]  = mapped_column(Text, nullable=False)  # "PDF", "Excel", ...
    FormatoFactura:Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
