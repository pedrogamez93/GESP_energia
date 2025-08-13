from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserPublic
from app.services.auth_service import login_and_issue_token
from app.core.security import get_current_user

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    token, user_public = login_and_issue_token(db, payload.username_or_email, payload.password)
    return TokenResponse(access_token=token, user=user_public)

@router.get("/me", response_model=UserPublic)
def me(current: UserPublic = Depends(get_current_user)):
    return current
