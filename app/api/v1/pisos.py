from typing import Annotated
from fastapi import APIRouter, Depends, Path, status, Request, Response
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.db.models.piso import Piso
from app.db.models.area import Area

router = APIRouter(prefix="/api/v1/pisos", tags=["Pisos"])
DbDep = Annotated[Session, Depends(get_db)]

def _current_user_id(request: Request) -> str | None:
    return getattr(request.state, "user_id", None) or request.headers.get("X-User-Id")

@router.post("/delete/{piso_id}", status_code=status.HTTP_204_NO_CONTENT,
             summary="Soft-delete de piso + áreas hijas (paridad .NET api/Pisos/delete/{id})")
def delete_piso(
    piso_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    request: Request
):
    p = db.query(Piso).filter(Piso.Id == piso_id).first()
    if not p:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    now = datetime.utcnow()
    user_id = _current_user_id(request)

    if p.Active:
        p.Active = False
        p.UpdatedAt = now
        p.ModifiedBy = user_id
        p.Version = (p.Version or 0) + 1

    # Soft-delete en cascada de Areas del piso
    areas = db.query(Area).filter(Area.PisoId == piso_id, Area.Active == True).all()
    for a in areas:
        a.Active = False
        a.UpdatedAt = now
        a.ModifiedBy = user_id
        a.Version = (a.Version or 0) + 1

    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
