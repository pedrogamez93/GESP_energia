# app/db/models/unidades_pisos.py
from sqlalchemy import Table, Column, BigInteger, ForeignKey, PrimaryKeyConstraint
from app.db.base import Base

metadata = Base.metadata

UnidadesPisos = Table(
    "UnidadesPisos",
    metadata,
    Column("UnidadId", BigInteger, ForeignKey("dbo.Unidades.Id", ondelete="RESTRICT"), nullable=False),
    Column("PisoId",   BigInteger, ForeignKey("dbo.Pisos.Id", ondelete="RESTRICT"),     nullable=False),
    PrimaryKeyConstraint("UnidadId", "PisoId", name="PK_UnidadesPisos"),
    schema="dbo",
    extend_existing=True,  # protege contra redefiniciones accidentales
)
