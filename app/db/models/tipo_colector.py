from __future__ import annotations
from sqlalchemy import BigInteger, Text, Float, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TipoColector(Base):
    __tablename__ = "TiposColectores"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)

    # Parámetros típicos ACS (no nulos; el servicio setea defaults=0 para evitar NULL)
    Eta0: Mapped[float] = mapped_column(Float, nullable=False)              # Eficiencia óptica (η0)
    A1: Mapped[float] = mapped_column(Float, nullable=False)                # Coef. pérdidas lineales
    A2: Mapped[float] = mapped_column(Float, nullable=False)                # Coef. pérdidas cuadráticas
    AreaApertura: Mapped[float] = mapped_column(Float, nullable=False)      # m²
    Costo: Mapped[float] = mapped_column(Float, nullable=False)             # costo de compra/instalación
    Costo_Mant: Mapped[float] = mapped_column(Float, nullable=False)        # costo de mantención anual
    VidaUtil: Mapped[int] = mapped_column(Integer, nullable=False)          # años

    # opcional para listados genéricos (si no existe en DB, no lo uses)
    Active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
