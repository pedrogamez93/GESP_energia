from sqlalchemy import Table, Column, BigInteger, ForeignKey
from app.db.base import Base

# Tabla intermedia Piso <-> Unidad
UnidadesPisos = Table(
    "UnidadesPisos",
    Base.metadata,
    Column("UnidadId", BigInteger, ForeignKey("dbo.Unidades.Id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column("PisoId",   BigInteger, ForeignKey("dbo.Pisos.Id", ondelete="CASCADE"),     primary_key=True, nullable=False),
    schema="dbo",
)
