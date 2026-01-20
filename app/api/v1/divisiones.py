from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.session import get_db
from app.schemas.auth import UserPublic
from app.schemas.division import (
    DivisionBusquedaEspecificaPage,
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
from app.schemas.division_full_update import DivisionFullUpdate
from app.schemas.division import DivisionCreate
from app.services.division_service import DivisionService

router = APIRouter(prefix="/api/v1/divisiones", tags=["Divisiones"])
svc = DivisionService()
DbDep = Annotated[Session, Depends(get_db)]


# ------------------------------------------------------------
# Helpers de usuario / auth
# ------------------------------------------------------------
def _current_user_id(request: Request) -> str | None:
    return getattr(request.state, "user_id", None) or request.headers.get("X-User-Id")


def _user_roles_upper(user: UserPublic) -> set[str]:
    roles = getattr(user, "roles", None) or getattr(user, "Roles", None) or []
    return {str(r).upper() for r in roles}


def _user_id_str(user: UserPublic) -> str:
    return str(getattr(user, "id", None) or getattr(user, "Id", None) or "")


def _enforce_self_or_admin(user: UserPublic, path_user_id: str) -> None:
    roles = _user_roles_upper(user)

    if "ADMINISTRADOR" in roles or "ADMIN" in roles or "SUPERADMIN" in roles:
        return

    token_user_id = _user_id_str(user)
    if not token_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido (sin id de usuario)",
        )

    if token_user_id != str(path_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes consultar tus propias unidades/divisiones",
        )


# ------------------------------------------------------------
# GET públicos
# ------------------------------------------------------------
@router.get("", response_model=DivisionPage, summary="Listado paginado")
def list_divisiones(
    db: DbDep,
    q: Optional[str] = Query(None, description="Busca en Dirección o Nombre"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=500),
    active: Optional[bool] = Query(None),
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


@router.post(
    "",
    response_model=DivisionDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear (FULL)",
)
def create_division_full(
    payload: DivisionCreate,
    db: DbDep,
    request: Request,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    # ✅ CRÍTICO: evita mandar campos en null (ej: ServicioId=None) que rompen SQL Server
    data = payload.model_dump(exclude_unset=True, exclude_none=True)

    return svc.create_full(
        db=db,
        payload=data,
        user_id=_current_user_id(request),
    )


@router.get("/select", response_model=List[DivisionSelectDTO], summary="(picker) Id/Dirección")
def select_divisiones(
    db: DbDep,
    q: Optional[str] = Query(None),
    ServicioId: Optional[int] = Query(None),
    RegionId: Optional[int] = Query(None),
):
    rows = svc.list_select(db, q, ServicioId, RegionId)
    return [DivisionSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]


@router.get(
    "/busqueda-especifica",
    response_model=DivisionBusquedaEspecificaPage,
    summary="Búsqueda específica paginada",
)
def list_divisiones_busqueda_especifica(
    db: DbDep,
    q: Optional[str] = Query(None),
    ServicioId: Optional[int] = Query(None),
    RegionId: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    return svc.list_busqueda_especifica(
        db=db,
        q=q,
        servicio_id=ServicioId,
        region_id=RegionId,
        page=page,
        page_size=page_size,
    )


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
def get_divisiones_by_edificio(
    edificio_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.by_edificio(db, edificio_id)


@router.get("/region/{region_id}", response_model=List[DivisionListDTO], summary="Por región")
def get_divisiones_by_region(
    region_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.by_region(db, region_id)


# ------------------------------------------------------------
# Por usuario (ADMIN + gestores, self-only)
# ------------------------------------------------------------
@router.get(
    "/usuario/{user_id}",
    response_model=List[DivisionListDTO],
    summary="Por usuario (UsuariosDivisiones)",
)
def get_divisiones_by_user(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    auth_user: Annotated[
        UserPublic,
        Depends(
            require_roles(
                "ADMINISTRADOR",
                "GESTOR_SERVICIO",
                "GESTOR_UNIDAD",
                "GESTOR DE CONSULTA",
            )
        ),
    ],
):
    _enforce_self_or_admin(auth_user, user_id)
    return svc.by_user(db, user_id)


# ------------------------------------------------------------
# Observaciones / flags / años
# ------------------------------------------------------------
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


@router.get("/inexistencia-eyv/{division_id}", response_model=ObservacionInexistenciaDTO)
def get_inexistencia_eyv(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
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


@router.patch("/{division_id}", response_model=DivisionDTO)
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


@router.put("/{division_id}/activar", response_model=DivisionDTO)
def activar_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    request: Request,
):
    return svc.set_active_cascada(db, division_id, True, _current_user_id(request))


@router.put("/{division_id}/desactivar", response_model=DivisionDTO)
def desactivar_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    request: Request,
):
    return svc.set_active_cascada(db, division_id, False, _current_user_id(request))


@router.put("/{division_id}/full", response_model=DivisionDTO)
def update_division_full(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: DivisionFullUpdate,
    db: DbDep,
    request: Request,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    data = payload.model_dump(exclude_unset=True, exclude_none=True)

    return svc.update_full(
        db,
        division_id,
        payload=data,
        user_id=_current_user_id(request),
    )
