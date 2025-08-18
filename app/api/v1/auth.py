from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.schemas.auth import TokenResponse
from app.services.auth_service import login_and_issue_token

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    token, user = login_and_issue_token(db, form.username, form.password)
    return TokenResponse(access_token=token, user=user)
