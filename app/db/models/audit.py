from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, DateTime, String, Integer, text

class Base(DeclarativeBase): ...
class AuditLog(Base):
    __tablename__ = "user_activity_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=False), server_default=text("SYSUTCDATETIME()"))
    action: Mapped[str] = mapped_column(String(32))
    resource_type: Mapped[str | None] = mapped_column(String(128))
    resource_id: Mapped[str | None] = mapped_column(String(128))
    http_method: Mapped[str | None] = mapped_column(String(10))
    path: Mapped[str | None] = mapped_column(String(512))
    status_code: Mapped[int | None] = mapped_column(Integer)
    actor_id: Mapped[str | None] = mapped_column(String(64))
    actor_username: Mapped[str | None] = mapped_column(String(150))
    session_id: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    changes_json: Mapped[str | None] = mapped_column()
    request_body_sha256: Mapped[str | None] = mapped_column(String(64))
