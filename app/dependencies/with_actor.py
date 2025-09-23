# app/dependencies/with_actor.py
from fastapi import Depends
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.services.auth_service import get_current_user  # ajusta al tuyo real

def with_actor(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db.info["actor"] = {
        "id": str(getattr(current_user, "id", None)),
        "username": getattr(current_user, "username", None),
    }
    return db
