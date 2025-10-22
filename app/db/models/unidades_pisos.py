from sqlalchemy import Table, Column, BigInteger, ForeignKey, PrimaryKeyConstraint
from app.db.base import Base

metadata = Base.metadata

UnidadesPisos = Table(
    "UnidadesPisos",
    metadata,
    Column("UnidadId", BigInteger, ForeignKey("dbo.Unidades.Id"), nullable=False),
    Column("PisoId", BigInteger, ForeignKey("dbo.Pisos.Id"), nullable=False),
    PrimaryKeyConstraint("UnidadId", "PisoId", name="PK_UnidadesPisos"),
    schema="dbo",
    extend_existing=True,  # 🔑 evita conflicto si ya estaba cargada
)
