from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class PasswordResetToken(Base):
    __tablename__ = "PasswordResetTokens"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    UserId: Mapped[str] = mapped_column(Text, ForeignKey("dbo.AspNetUsers.Id"), nullable=False)
    TokenHash: Mapped[str] = mapped_column(Text, nullable=False)   # SHA-256 del token
    ExpiresAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    UsedAt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    Ip: Mapped[str | None] = mapped_column(Text)

    user = relationship("AspNetUser")
