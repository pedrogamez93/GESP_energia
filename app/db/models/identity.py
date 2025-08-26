# app/db/models/identity.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    String, Boolean, Integer, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base


# =========================
# dbo.AspNetUsers
# =========================
class AspNetUser(Base):
    __tablename__ = "AspNetUsers"
    __table_args__ = {"schema": "dbo"}

    # Clave (NVARCHAR(450))
    Id: Mapped[str] = mapped_column(String(450), primary_key=True)

    # Identity core
    UserName: Mapped[str | None] = mapped_column(String(256))
    NormalizedUserName: Mapped[str | None] = mapped_column(String(256))
    Email: Mapped[str | None] = mapped_column(String(256))
    NormalizedEmail: Mapped[str | None] = mapped_column(String(256))
    EmailConfirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    PasswordHash: Mapped[str | None] = mapped_column(Text)           # nvarchar(max)
    SecurityStamp: Mapped[str | None] = mapped_column(Text)
    ConcurrencyStamp: Mapped[str | None] = mapped_column(Text)

    PhoneNumber: Mapped[str | None] = mapped_column(Text)
    PhoneNumberConfirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    TwoFactorEnabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # En SQL: datetimeoffset(7) NULL → timezone=True
    LockoutEnd: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    LockoutEnabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    AccessFailedCount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Campos de negocio extra (nvarchar(max) salvo donde se indica)
    Nombres: Mapped[str | None] = mapped_column(Text)
    Apellidos: Mapped[str | None] = mapped_column(Text)
    Active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)        # bit NULL
    Address: Mapped[str | None] = mapped_column(Text)
    City: Mapped[str | None] = mapped_column(Text)
    PostalCode: Mapped[str | None] = mapped_column(Text)
    Cargo: Mapped[str | None] = mapped_column(Text)
    Certificado: Mapped[bool | None] = mapped_column(Boolean, nullable=True)   # bit NULL
    Nacionalidad: Mapped[str | None] = mapped_column(Text)
    Rut: Mapped[str | None] = mapped_column(Text)
    Validado: Mapped[bool | None] = mapped_column(Boolean, nullable=True)      # bit NULL
    OldId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    NumeroTelefonoOpcional: Mapped[str | None] = mapped_column(Text)

    # FKs
    ComunaId: Mapped[int] = mapped_column(ForeignKey("dbo.Comunas.Id", ondelete="CASCADE"), nullable=False)
    SexoId: Mapped[int | None] = mapped_column(ForeignKey("dbo.Sexo.Id"), nullable=True)

    # Timestamps (datetime2(7) → timezone=False)
    CreatedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    CreatedBy: Mapped[str | None] = mapped_column(Text)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    UpdatedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    # M2M con Roles (pivot dbo.AspNetUserRoles)
    roles: Mapped[list["AspNetRole"]] = relationship(
        "AspNetRole",
        secondary="dbo.AspNetUserRoles",
        back_populates="users",
        lazy="joined",
    )

    # Colecciones Identity
    user_claims: Mapped[list["AspNetUserClaim"]] = relationship(
        "AspNetUserClaim", back_populates="user", cascade="all, delete-orphan"
    )
    logins: Mapped[list["AspNetUserLogin"]] = relationship(
        "AspNetUserLogin", back_populates="user", cascade="all, delete-orphan"
    )
    tokens: Mapped[list["AspNetUserToken"]] = relationship(
        "AspNetUserToken", back_populates="user", cascade="all, delete-orphan"
    )


# =========================
# dbo.AspNetRoles
# =========================
class AspNetRole(Base):
    __tablename__ = "AspNetRoles"
    __table_args__ = {"schema": "dbo"}

    # Clave (NVARCHAR(450))
    Id: Mapped[str] = mapped_column(String(450), primary_key=True)

    Name: Mapped[str | None] = mapped_column(String(256))
    NormalizedName: Mapped[str | None] = mapped_column(String(256))
    ConcurrencyStamp: Mapped[str | None] = mapped_column(Text)

    # Extras de tu BD
    Nombre: Mapped[str | None] = mapped_column(Text)            # etiqueta amigable
    OldId: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    DependeDelRoleId: Mapped[str | None] = mapped_column(Text)  # jerarquía (string sin FK)

    users: Mapped[list["AspNetUser"]] = relationship(
        "AspNetUser",
        secondary="dbo.AspNetUserRoles",
        back_populates="roles",
    )

    role_claims: Mapped[list["AspNetRoleClaim"]] = relationship(
        "AspNetRoleClaim", back_populates="role", cascade="all, delete-orphan"
    )


# =========================
# dbo.AspNetUserRoles (pivot)
# =========================
class AspNetUserRole(Base):
    __tablename__ = "AspNetUserRoles"
    __table_args__ = {"schema": "dbo"}

    # PK compuesta (como en la BD)
    UserId: Mapped[str] = mapped_column(
        String(450), ForeignKey("dbo.AspNetUsers.Id", ondelete="CASCADE"), primary_key=True
    )
    RoleId: Mapped[str] = mapped_column(
        String(450), ForeignKey("dbo.AspNetRoles.Id", ondelete="CASCADE"), primary_key=True
    )


# =========================
# dbo.AspNetRoleClaims
# =========================
class AspNetRoleClaim(Base):
    __tablename__ = "AspNetRoleClaims"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    RoleId: Mapped[str] = mapped_column(
        String(450), ForeignKey("dbo.AspNetRoles.Id", ondelete="CASCADE"), nullable=False
    )
    ClaimType: Mapped[str | None] = mapped_column(Text)
    ClaimValue: Mapped[str | None] = mapped_column(Text)

    role: Mapped["AspNetRole"] = relationship("AspNetRole", back_populates="role_claims")


# =========================
# dbo.AspNetUserClaims
# =========================
class AspNetUserClaim(Base):
    __tablename__ = "AspNetUserClaims"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    UserId: Mapped[str] = mapped_column(
        String(450), ForeignKey("dbo.AspNetUsers.Id", ondelete="CASCADE"), nullable=False
    )
    ClaimType: Mapped[str | None] = mapped_column(Text)
    ClaimValue: Mapped[str | None] = mapped_column(Text)

    user: Mapped["AspNetUser"] = relationship("AspNetUser", back_populates="user_claims")


# =========================
# dbo.AspNetUserLogins
# =========================
class AspNetUserLogin(Base):
    __tablename__ = "AspNetUserLogins"
    __table_args__ = {"schema": "dbo"}

    # PK compuesta (LoginProvider + ProviderKey)
    LoginProvider: Mapped[str] = mapped_column(String(450), primary_key=True)
    ProviderKey: Mapped[str] = mapped_column(String(450), primary_key=True)

    ProviderDisplayName: Mapped[str | None] = mapped_column(Text)
    UserId: Mapped[str] = mapped_column(
        String(450), ForeignKey("dbo.AspNetUsers.Id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["AspNetUser"] = relationship("AspNetUser", back_populates="logins")


# =========================
# dbo.AspNetUserTokens
# =========================
class AspNetUserToken(Base):
    __tablename__ = "AspNetUserTokens"
    __table_args__ = {"schema": "dbo"}

    # PK compuesta (UserId + LoginProvider + Name)
    UserId: Mapped[str] = mapped_column(
        String(450), ForeignKey("dbo.AspNetUsers.Id", ondelete="CASCADE"), primary_key=True
    )
    LoginProvider: Mapped[str] = mapped_column(String(450), primary_key=True)
    Name: Mapped[str] = mapped_column(String(450), primary_key=True)

    Value: Mapped[str | None] = mapped_column(Text)

    user: Mapped["AspNetUser"] = relationship("AspNetUser", back_populates="tokens")
