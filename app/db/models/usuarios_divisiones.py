from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, BigInteger, ForeignKey, Index
from app.db.base import Base

class UsuarioDivision(Base):
    __tablename__ = "UsuariosDivisiones"
    __table_args__ = (
        Index("IX_UsuariosDivisiones_UsuarioId", "UsuarioId"),
        Index("IX_UsuariosDivisiones_DivisionId", "DivisionId"),
        {"schema": "dbo"},
    )

    UsuarioId: Mapped[str] = mapped_column(
        String(450), ForeignKey("dbo.AspNetUsers.Id", ondelete="CASCADE"), primary_key=True
    )
    DivisionId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.Divisiones.Id", ondelete="CASCADE"), primary_key=True
    )
