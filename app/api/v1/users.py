from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.schemas.user import UserCreate, UserOut
from app.services.user_service import create_user, get_users

router = APIRouter()

@router.post("/", response_model=UserOut)
def create(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user)

@router.get("/", response_model=list[UserOut])
def read_users(db: Session = Depends(get_db)):
    return get_users(db)
