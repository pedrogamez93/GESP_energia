from sqlalchemy import String, BigInteger, ForeignKey, PrimaryKeyConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class UsuarioServicio(Base):
    __tablename__ = "UsuariosServicios"
    __table_args__ = (
        PrimaryKeyConstraint("ServicioId", "UsuarioId", name="PK_UsuariosServicios"),
        Index("IX_UsuariosServicios_UsuarioId", "UsuarioId"),
        Index("IX_UsuariosServicios_ServicioId", "ServicioId"),
        {"schema": "dbo"},
    )

    UsuarioId: Mapped[str] = mapped_column(
        "UsuarioId",
        String(450),
        ForeignKey("dbo.AspNetUsers.Id", ondelete="CASCADE"),
        nullable=False,
    )
    ServicioId: Mapped[int] = mapped_column(
        "ServicioId",
        BigInteger,
        ForeignKey("dbo.Servicios.Id", ondelete="CASCADE"),
        nullable=False,
    )
