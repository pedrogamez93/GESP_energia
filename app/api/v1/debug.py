from fastapi import APIRouter, Depends
from app.core.security import get_current_user

dbg = APIRouter(prefix="/api/v1/debug", tags=["Debug"])

@dbg.get("/me")
def me(u = Depends(get_current_user)):
    return {"id": u.id, "username": u.username, "roles": u.roles}