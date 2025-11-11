from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.session import get_db
from app.schemas.auth import UserPublic
from app.schemas.division import (
    DivisionAniosDTO,
    DivisionDTO,
    DivisionListDTO,
    DivisionPage,
    DivisionPatchDTO,
    DivisionSelectDTO,
    ObservacionDTO,
    ObservacionInexistenciaDTO,
    OkMessage,
    ReportaResiduosDTO,
)
from app.services.division_service import DivisionService

router = APIRouter(prefix="/api/v1/divisiones", tags=["Divisiones"])
svc = DivisionService()
DbDep = Annotated[Session, Depends(get_db)]


def _current_user_id(request: Request) -> str | None:
    return getattr(request.state, "user_id", None) or request.headers.get("X-User-Id")


# ---- GET públicos (paginado, liviano) ----
@router.get("", response_model=DivisionPage, summary="Listado paginado")
def list_divisiones(
    db: DbDep,
    q: Optional[str] = Query(None, description="Busca en Dirección o Nombre (case-insensitive)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),   # default 15
    active: Optional[bool] = Query(True),
    ServicioId: Optional[int] = Query(None),
    RegionId: Optional[int] = Query(None),
    ProvinciaId: Optional[int] = Query(None),
    ComunaId: Optional[int] = Query(None),
):
    return svc.list(
        db=db,
        q=q,
        page=page,
        page_size=page_size,
        active=active,
        servicio_id=ServicioId,
        region_id=RegionId,
        provincia_id=ProvinciaId,
        comuna_id=ComunaId,
    )


@router.get("/select", response_model=List[DivisionSelectDTO], summary="(picker) Id/Dirección")
def select_divisiones(
    db: DbDep,
    q: Optional[str] = Query(None, description="Busca en Dirección"),
    ServicioId: Optional[int] = Query(None),
):
    rows = svc.list_select(db, q, ServicioId)
    return [DivisionSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]


@router.get("/{division_id}", response_model=DivisionDTO, summary="Detalle")
def get_division(division_id: Annotated[int, Path(..., ge=1)], db: DbDep):
    return svc.get(db, division_id)


@router.get("/servicio/{servicio_id}", response_model=List[DivisionListDTO], summary="Por servicio")
def get_divisiones_by_servicio(
    servicio_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    searchText: Optional[str] = Query(None),
):
    return svc.by_servicio(db, servicio_id, searchText)


@router.get("/edificio/{edificio_id}", response_model=List[DivisionListDTO], summary="Por edificio")
def get_divisiones_by_edificio(edificio_id: Annotated[int, Path(..., ge=1)], db: DbDep):
    return svc.by_edificio(db, edificio_id)


@router.get("/region/{region_id}", response_model=List[DivisionListDTO], summary="Por región")
def get_divisiones_by_region(region_id: Annotated[int, Path(..., ge=1)], db: DbDep):
    return svc.by_region(db, region_id)


# ---- Por usuario (ADMIN) ----
@router.get(
    "/usuario/{user_id}",
    response_model=List[DivisionListDTO],
    summary="Por usuario (vía UsuariosDivisiones)",
)
def get_divisiones_by_user(
    user_id: Annotated[str, Path(...)],
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
    db: DbDep,
):
    return svc.by_user(db, user_id)


# ---------------------------
# Paridad con .NET (observaciones / flags / años)
# ---------------------------

@router.get("/observacion-papel/{division_id}", response_model=ObservacionDTO)
def get_obs_papel(division_id: Annotated[int, Path(..., ge=1)], db: DbDep):
    return svc.get_observacion_papel(db, division_id)


@router.put("/observacion-papel/{division_id}", response_model=OkMessage)
def put_obs_papel(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: ObservacionDTO,
    db: DbDep,
):
    svc.set_observacion_papel(db, division_id, payload)
    return OkMessage()


@router.get("/observacion-residuos/{division_id}", response_model=ObservacionDTO)
def get_obs_residuos(division_id: Annotated[int, Path(..., ge=1)], db: DbDep):
    return svc.get_observacion_residuos(db, division_id)


@router.put("/observacion-residuos/{division_id}", response_model=OkMessage)
def put_obs_residuos(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: ObservacionDTO,
    db: DbDep,
):
    svc.set_observacion_residuos(db, division_id, payload)
    return OkMessage()


@router.get("/reporta-residuos/{division_id}", response_model=ReportaResiduosDTO)
def get_rep_residuos(division_id: Annotated[int, Path(..., ge=1)], db: DbDep):
    return svc.get_reporta_residuos(db, division_id)


@router.put("/reporta-residuos/{division_id}", response_model=OkMessage)
def put_rep_residuos(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: ReportaResiduosDTO,
    db: DbDep,
):
    svc.set_reporta_residuos(db, division_id, payload)
    return OkMessage()


@router.put("/reporta-residuos-no-reciclados/{division_id}", response_model=OkMessage)
def put_rep_residuos_no_rec(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: ReportaResiduosDTO,
    db: DbDep,
):
    svc.set_reporta_residuos_no_reciclados(db, division_id, payload)
    return OkMessage()


@router.get("/observacion-agua/{division_id}", response_model=ObservacionDTO)
def get_obs_agua(division_id: Annotated[int, Path(..., ge=1)], db: DbDep):
    return svc.get_observacion_agua(db, division_id)


@router.put("/justifica-agua/{division_id}", response_model=OkMessage)
def put_obs_agua(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: ObservacionDTO,
    db: DbDep,
):
    svc.set_observacion_agua(db, division_id, payload)
    return OkMessage()


@router.get("/inexistencia-eyv/{division_id}", response_model=ObservacionInexistenciaDTO)
def get_inexistencia_eyv(division_id: Annotated[int, Path(..., ge=1)], db: DbDep):
    return svc.get_inexistencia_eyv(db, division_id)


@router.put("/inexistencia-eyv/{division_id}", response_model=OkMessage)
def put_inexistencia_eyv(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: ObservacionInexistenciaDTO,
    db: DbDep,
):
    svc.set_inexistencia_eyv(db, division_id, payload)
    return OkMessage()


@router.post("/set-inicio-gestion", status_code=status.HTTP_204_NO_CONTENT)
def set_inicio_gestion(payload: DivisionAniosDTO, db: DbDep):
    svc.set_anios(db, payload, set_gestion=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/set-resto-items", status_code=status.HTTP_204_NO_CONTENT)
def set_resto_items(payload: DivisionAniosDTO, db: DbDep):
    svc.set_anios(db, payload, set_gestion=False)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{division_id}", response_model=DivisionDTO, summary="Patch parcial de división")
def patch_division(
    division_id: Annotated[int, Path(..., ge=1)],
    patch: DivisionPatchDTO,
    db: DbDep,
):
    return svc.patch(db, division_id, patch)


@router.delete("/delete/{division_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    request: Request,
):
    svc.delete_soft_cascada(db, division_id, _current_user_id(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{division_id}/activar", response_model=DivisionDTO, summary="Activar división (soft, en cascada)")
def activar_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    request: Request,
):
    return svc.set_active_cascada(db, division_id, active=True, user_id=_current_user_id(request))


@router.put("/{division_id}/desactivar", response_model=DivisionDTO, summary="Desactivar división (soft, en cascada)")
def desactivar_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    request: Request,
):
    return svc.set_active_cascada(db, division_id, active=False, user_id=_current_user_id(request))
