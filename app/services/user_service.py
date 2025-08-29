from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc, desc
from app.schemas.user import UserCreate
from app.db.models.user import User  # tu modelo ORM (AspNetUser/User)
from app.utils.hash import Hash


# --- utilidades internas para resolver nombres según el modelo ---
def _resolve_attr(cls, *names):
    """Devuelve el atributo del modelo que exista primero."""
    for name in names:
        if hasattr(cls, name):
            return getattr(cls, name)
    return None

def _resolve_name(cls, *names):
    """Devuelve el nombre de atributo que exista primero."""
    for name in names:
        if hasattr(cls, name):
            return name
    return None


def create_user(db: Session, user: UserCreate):
    email_norm = user.email.strip().lower()

    # Resuelve nombres reales del modelo (PascalCase o snake_case)
    email_field      = _resolve_name(User, "email", "Email")
    full_name_field  = _resolve_name(User, "full_name", "FullName")
    password_field   = _resolve_name(User, "hashed_password", "PasswordHash")

    if not (email_field and password_field):
        raise RuntimeError("No se pudieron resolver los campos de email/contraseña en el modelo User.")

    data = {
        email_field: email_norm,
        password_field: Hash.bcrypt(user.password),
    }
    if full_name_field:
        data[full_name_field] = user.full_name

    db_user = User(**data)
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("El email ya existe")
    db.refresh(db_user)
    return db_user


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "Id",
    sort_dir: str = "asc",
):
    """
    MSSQL exige ORDER BY cuando usamos OFFSET/FETCH.
    Además, permitimos sort_by en varios alias seguros para evitar inyección.
    """

    # Columnas posibles en ambos estilos de naming
    id_col        = _resolve_attr(User, "Id", "id")
    email_col     = _resolve_attr(User, "Email", "email")
    full_name_col = _resolve_attr(User, "FullName", "full_name")
    created_col   = _resolve_attr(User, "CreatedAt", "created_at", "Created", "createdAt")

    # Mapa de columnas permitidas para ordenar (aceptamos varios alias)
    allowed_cols = {
        "Id": id_col, "id": id_col,
        "Email": email_col, "email": email_col,
        "FullName": full_name_col, "full_name": full_name_col,
        "CreatedAt": created_col, "created_at": created_col,
    }

    # Columna por defecto: PK si existe, si no, email
    default_col = id_col or email_col
    col = allowed_cols.get(sort_by, default_col) or default_col

    order_expr = asc(col) if sort_dir.lower() == "asc" else desc(col)

    return (
        db.query(User)
        .order_by(order_expr)   # <-- clave para MSSQL con OFFSET/LIMIT
        .offset(skip)
        .limit(limit)
        .all()
    )
