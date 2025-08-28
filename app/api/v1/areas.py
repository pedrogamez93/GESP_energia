from typing import Annotated
from fastapi import APIRouter, Depends, Path, status, Request, Response
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.db.models.area import Area

router = APIRouter(prefix="/api/v1/areas", tags=["Áreas"])
DbDep = Annotated[Session, Depends(get_db)]

def _current_user_id(request: Request) -> str | None:
    return getattr(request.state, "user_id", None) or request.headers.get("X-User-Id")

@router.post("/delete/{area_id}", status_code=status.HTTP_204_NO_CONTENT,
             summary="Soft-delete de área (paridad .NET api/Areas/delete/{id})")
def delete_area(
    area_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    request: Request
):
    a = db.query(Area).filter(Area.Id == area_id).first()
    if not a:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    if not a.Active:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    now = datetime.utcnow()
    a.Active = False
    a.UpdatedAt = now
    a.ModifiedBy = _current_user_id(request)
    a.Version = (a.Version or 0) + 1
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
