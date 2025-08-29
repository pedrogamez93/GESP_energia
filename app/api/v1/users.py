from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import UserCreate, UserOut
from app.services.user_service import create_user, get_users

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

@router.post("", response_model=UserOut)
def create(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user)

@router.get("", response_model=list[UserOut])
def read_users(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(50, ge=1, le=200, description="Registros a devolver"),
    sort_by: str = Query("Id", description="Columna para ordenar"),
    sort_dir: str = Query("asc", pattern="^(?i)(asc|desc)$", description="Dirección de orden"),
    status: Literal["active", "inactive", "all"] = Query(
        "active", description="Filtrar por estado: active | inactive | all"
    ),
):
    """Lista usuarios con paginación, orden y filtro de estado (MSSQL friendly)."""
    return get_users(
        db,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_dir=sort_dir,
        status=status,
    )
