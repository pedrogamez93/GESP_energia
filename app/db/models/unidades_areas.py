from sqlalchemy import Table, Column, BigInteger, ForeignKey, PrimaryKeyConstraint
from app.db.base import Base

metadata = Base.metadata

UnidadesAreas = Table(
    "UnidadesAreas",
    metadata,
    Column("UnidadId", BigInteger, ForeignKey("dbo.Unidades.Id"), nullable=False),
    Column("AreaId", BigInteger, ForeignKey("dbo.Areas.Id"), nullable=False),
    PrimaryKeyConstraint("UnidadId", "AreaId", name="PK_UnidadesAreas"),
    schema="dbo",
    extend_existing=True,  # 🔑 evita conflicto si ya estaba cargada
)
