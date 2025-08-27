from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.medidor import (
    MedidorInteligenteDTO,
    MedidorInteligenteCreate,
    MedidorInteligenteUpdate,
    IdsPayload,
)
from app.services.medidor_inteligente_service import MedidorInteligenteService

router = APIRouter(prefix="/api/v1/medidores-inteligentes", tags=["Medidores inteligentes"])
svc = MedidorInteligenteService()
DbDep = Annotated[Session, Depends(get_db)]

# ---- Buscar por ChileMedidoId (si existe) ----
@router.get("/buscar", response_model=MedidorInteligenteDTO)
def buscar(
    db: DbDep,
    ChileMedidoId: int = Query(..., ge=1),
):
    obj = svc.find_by_chilemedido(db, ChileMedidoId)
    if not obj:
        # si no existe, devolvemos objeto vacío-like? mejor 404, pero el .NET podría crear on-demand.
        # aquí devolvemos 404 para ser estrictos.
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No existe medidor inteligente con ese ChileMedidoId")
    divs, edis, srvs = svc.get_detail_ids(db, obj.Id)
    return MedidorInteligenteDTO(Id=obj.Id, ChileMedidoId=obj.ChileMedidoId,
                                 DivisionIds=divs, EdificioIds=edis, ServicioIds=srvs)

# ---- Crear ----
@router.post("", response_model=MedidorInteligenteDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Crear medidor inteligente")
def crear(
    payload: MedidorInteligenteCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = svc.create(db, payload.ChileMedidoId, created_by=current_user.id)
    # si vienen vínculos en el payload, los aplicamos
    if payload.DivisionIds:
        svc.set_divisiones(db, obj.Id, payload.DivisionIds)
    if payload.EdificioIds:
        svc.set_edificios(db, obj.Id, payload.EdificioIds)
    if payload.ServicioIds:
        svc.set_servicios(db, obj.Id, payload.ServicioIds)
    divs, edis, srvs = svc.get_detail_ids(db, obj.Id)
    return MedidorInteligenteDTO(Id=obj.Id, ChileMedidoId=obj.ChileMedidoId,
                                 DivisionIds=divs, EdificioIds=edis, ServicioIds=srvs)

# ---- Update simple (ChileMedidoId/Active) ----
@router.put("/{med_int_id}", response_model=MedidorInteligenteDTO,
            summary="(ADMINISTRADOR) Actualiza datos del medidor inteligente")
def actualizar(
    med_int_id: Annotated[int, Path(..., ge=1)],
    payload: MedidorInteligenteUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = svc.get(db, med_int_id)
    if payload.ChileMedidoId is not None:
        obj = svc.update_chilemedido(db, med_int_id, payload.ChileMedidoId, modified_by=current_user.id)
    # Active lo tocamos directo (no siempre existe en payload)
    if payload.Active is not None:
        obj.Active = payload.Active
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = __import__("datetime").datetime.utcnow()
        obj.ModifiedBy = current_user.id
        db.commit(); db.refresh(obj)
    divs, edis, srvs = svc.get_detail_ids(db, obj.Id)
    return MedidorInteligenteDTO(Id=obj.Id, ChileMedidoId=obj.ChileMedidoId,
                                 DivisionIds=divs, EdificioIds=edis, ServicioIds=srvs)

# ---- Reemplazar vínculos ----
@router.put("/{med_int_id}/divisiones", response_model=List[int],
            summary="(ADMINISTRADOR) Reemplaza divisiones vinculadas")
def set_divisiones(
    med_int_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
    payload: IdsPayload | None = None,
):
    ids = payload.Ids if payload else []
    return svc.set_divisiones(db, med_int_id, ids)

@router.put("/{med_int_id}/edificios", response_model=List[int],
            summary="(ADMINISTRADOR) Reemplaza edificios vinculados")
def set_edificios(
    med_int_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
    payload: IdsPayload | None = None,
):
    ids = payload.Ids if payload else []
    return svc.set_edificios(db, med_int_id, ids)

@router.put("/{med_int_id}/servicios", response_model=List[int],
            summary="(ADMINISTRADOR) Reemplaza servicios vinculados")
def set_servicios(
    med_int_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
    payload: IdsPayload | None = None,
):
    ids = payload.Ids if payload else []
    return svc.set_servicios(db, med_int_id, ids)
