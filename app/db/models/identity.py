from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from app.db.base import Base

# dbo.AspNetUsers
class AspNetUser(Base):
    __tablename__ = "AspNetUsers"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[str] = mapped_column(UNIQUEIDENTIFIER, primary_key=True)
    UserName: Mapped[str | None] = mapped_column(String(256))
    NormalizedUserName: Mapped[str | None] = mapped_column(String(256))
    Email: Mapped[str | None] = mapped_column(String(256))
    NormalizedEmail: Mapped[str | None] = mapped_column(String(256))
    EmailConfirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    PasswordHash: Mapped[str | None] = mapped_column(String(1000))
    SecurityStamp: Mapped[str | None] = mapped_column(String(1000))
    ConcurrencyStamp: Mapped[str | None] = mapped_column(String(1000))
    PhoneNumber: Mapped[str | None] = mapped_column(String(64))
    PhoneNumberConfirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    TwoFactorEnabled: Mapped[bool] = mapped_column(Boolean, default=False)
    LockoutEnd: Mapped[DateTime | None]
    LockoutEnabled: Mapped[bool] = mapped_column(Boolean, default=True)
    AccessFailedCount: Mapped[int] = mapped_column(Integer, default=0)

    # Campos de negocio (los que uses realmente)
    Nombres: Mapped[str | None] = mapped_column(String(256))
    Apellidos: Mapped[str | None] = mapped_column(String(256))
    Active: Mapped[bool] = mapped_column(Boolean, default=True)
    Validado: Mapped[bool] = mapped_column(Boolean, default=True)

    roles: Mapped[list["AspNetRole"]] = relationship(
        "AspNetRole",
        secondary="dbo.AspNetUserRoles",
        back_populates="users",
        lazy="joined",
    )

# dbo.AspNetRoles
class AspNetRole(Base):
    __tablename__ = "AspNetRoles"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[str] = mapped_column(UNIQUEIDENTIFIER, primary_key=True)
    Name: Mapped[str | None] = mapped_column(String(256))
    NormalizedName: Mapped[str | None] = mapped_column(String(256))
    ConcurrencyStamp: Mapped[str | None] = mapped_column(String(1000))

    # Extras
    Nombre: Mapped[str | None] = mapped_column(String(256))

    users: Mapped[list[AspNetUser]] = relationship(
        "AspNetUser",
        secondary="dbo.AspNetUserRoles",
        back_populates="roles",
    )

# dbo.AspNetUserRoles (pivote)
class AspNetUserRole(Base):
    __tablename__ = "AspNetUserRoles"
    __table_args__ = (
        UniqueConstraint("UserId", "RoleId", name="UQ_AspNetUserRoles_UserId_RoleId"),
        {"schema": "dbo"},
    )

    UserId: Mapped[str] = mapped_column(UNIQUEIDENTIFIER, ForeignKey("dbo.AspNetUsers.Id"), primary_key=True)
    RoleId: Mapped[str] = mapped_column(UNIQUEIDENTIFIER, ForeignKey("dbo.AspNetRoles.Id"), primary_key=True)
