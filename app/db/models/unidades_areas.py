from sqlalchemy import Table, Column, BigInteger, ForeignKey
from app.db.base import Base

# Tabla intermedia Área <-> Unidad
UnidadesAreas = Table(
    "UnidadesAreas",
    Base.metadata,
    Column("UnidadId", BigInteger, ForeignKey("dbo.Unidades.Id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column("AreaId",   BigInteger, ForeignKey("dbo.Areas.Id", ondelete="CASCADE"),    primary_key=True, nullable=False),
    schema="dbo",
)
