# app/api/v1/servicios.py
from __future__ import annotations

from typing import List, Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Path, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.db.session import get_db
from app.db.models.usuarios_servicios import UsuarioServicio
from app.db.models.identity import AspNetRole, AspNetUserRole
from app.db.models.servicio import Servicio
from app.schemas.servicios import (
    ServicioDTO, ServicioListDTO, ServicioResponse,
    ServicioPatchDTO, DiagnosticoDTO,
    ServicioCreate, ServicioUpdate, ServicioEstadoDTO,
)
from app.schemas.auth import UserPublic
from app.core.app_validation import is_app_validate
from app.core.security import require_roles  # retorna UserPublic autenticado

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/api/v1/servicios", tags=["Servicios"])

# Aceptamos variaciones del nombre del rol admin para distintas BDs
ADMIN_ROLE_NAMES = {"ADMINISTRADOR", "ADMINISTRADORR", "Administrador"}


def _current_user_id(request: Request) -> str:
    """
    Compatibilidad para endpoints legacy / pruebas: toma el user_id desde
    request.state.user_id (middleware) o header X-User-Id.
    Si no viene, lanza 401.
    """
    uid = getattr(request.state, "user_id", None) or request.headers.get("X-User-Id")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falta userId")
    return uid


def _is_user_admin(db: Session, user_id: str) -> bool:
    """
    Chequea si el usuario tiene rol administrador. Considera Name y NormalizedName,
    ambos case-insensitive, y varias variantes conocidas del nombre del rol.
    """
    names_up = {n.upper() for n in ADMIN_ROLE_NAMES}
    stmt = (
        select(AspNetRole.Id)
        .join(AspNetUserRole, AspNetUserRole.RoleId == AspNetRole.Id)
        .where(AspNetUserRole.UserId == user_id)
        .where(
            (func.upper(AspNetRole.Name).in_(names_up))
            | (func.upper(AspNetRole.NormalizedName).in_(names_up))
        )
        .limit(1)
    )
    return db.execute(stmt).first() is not None


# ---------------------------
# Públicos / Compatibles (ya existentes)
# ---------------------------

@router.get(
    "/institucion/{institucion_id}/usuario/{user_id}",
    response_model=List[ServicioDTO],
    summary="Servicios por institución y usuario (respeta rol ADMIN)",
)
@router.get(  # alias legacy (OCULTO en Swagger)
    "/getByInstitucionIdAndUserId/{institucion_id}/{user_id}",
    response_model=List[ServicioDTO],
    include_in_schema=False,
)
def get_by_institucion_and_user(
    institucion_id: Annotated[int, Path(..., ge=1)],
    user_id: Annotated[str, Path(...)],
    db: DbDep,
) -> List[ServicioDTO]:
    admin = _is_user_admin(db, user_id)
    q = db.query(Servicio).filter(Servicio.Active.is_(True), Servicio.InstitucionId == institucion_id)
    if not admin:
        q = q.join(UsuarioServicio, UsuarioServicio.ServicioId == Servicio.Id)\
             .filter(UsuarioServicio.UsuarioId == user_id)
    servicios = q.order_by(Servicio.Nombre).all()
    return [ServicioDTO.model_validate(x) for x in servicios]


@router.get(
    "/lista/institucion/{institucion_id}",
    response_model=List[ServicioListDTO],
    summary="Lista ligera de servicios por institución (AllowAnonymous condicional)",
    description="Valida app (headers/clave) y devuelve (Id, Nombre) ordenado.",
)
@router.get(  # alias legacy (OCULTO en Swagger)
    "/getlist-by-institucionid/{institucion_id}",
    response_model=List[ServicioListDTO],
    include_in_schema=False,
)
def get_list_by_institucionid(
    institucion_id: Annotated[int, Path(..., ge=1)],
    request: Request,
    db: DbDep,
) -> List[ServicioListDTO]:
    # Si no envías los headers que espera is_app_validate -> 401
    if not is_app_validate(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized (app signature)")
    servicios = (
        db.query(Servicio)
          .filter(Servicio.Active.is_(True), Servicio.InstitucionId == institucion_id)
          .order_by(Servicio.Nombre)
          .all()
    )
    return [ServicioListDTO.model_validate(x) for x in servicios]


@router.get(
    "/usuario/{user_id}",
    response_model=ServicioResponse,
    summary="Servicios asociados a un user_id (respeta rol ADMIN)",
)
@router.get(  # alias legacy (OCULTO en Swagger)
    "/getByUserId/{user_id}",
    response_model=ServicioResponse,
    include_in_schema=False,
)
def get_by_user_id(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
) -> ServicioResponse:
    admin = _is_user_admin(db, user_id)
    q = db.query(Servicio).filter(Servicio.Active.is_(True))
    if not admin:
        q = q.join(UsuarioServicio, UsuarioServicio.ServicioId == Servicio.Id)\
             .filter(UsuarioServicio.UsuarioId == user_id)
    servicios = q.order_by(Servicio.Nombre).all()
    return ServicioResponse(Ok=True, Servicios=[ServicioDTO.model_validate(s) for s in servicios])


@router.get(
    "/usuario",
    response_model=ServicioResponse,
    summary="Servicios paginados del usuario autenticado (token) (respeta rol ADMIN)",
    description="Lee el user_id del token (dependencia de auth).",
)
@router.get(  # alias legacy (OCULTO en Swagger)
    "/getByUserIdPagin",
    response_model=ServicioResponse,
    include_in_schema=False,
)
def get_by_user_id_pagin(
    response: Response,
    db: DbDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 10,
    InstitucionId: Annotated[int | None, Query()] = None,
    Pmg: Annotated[bool, Query()] = False,
    # Solo autenticación (no exige rol específico). Si quieres exigir ADMIN, pasa "ADMINISTRADOR".
    current_user: Annotated[UserPublic, Depends(require_roles())] = None,
) -> ServicioResponse:
    current_user_id = current_user.id
    admin = _is_user_admin(db, current_user_id)

    base = db.query(Servicio).filter(Servicio.Active.is_(True))
    if not admin:
        base = (
            base.join(UsuarioServicio, UsuarioServicio.ServicioId == Servicio.Id)
                .filter(UsuarioServicio.UsuarioId == current_user_id)
        )

    if InstitucionId is not None:
        base = base.filter(Servicio.InstitucionId == InstitucionId)

    if Pmg:
        base = base.filter(Servicio.ReportaPMG.is_(True))

    id_query = base.with_entities(Servicio.Id).distinct()
    total = db.query(func.count()).select_from(id_query.subquery()).scalar()

    size = max(1, min(200, page_size))
    ids = (
        base.with_entities(Servicio.Id, Servicio.Nombre)
            .distinct()
            .order_by(Servicio.Nombre)
            .offset((page - 1) * size)
            .limit(size)
            .all()
    )
    ids_list = [row[0] for row in ids]

    items: list[Servicio] = []
    if ids_list:
        items = (
            db.query(Servicio)
              .filter(Servicio.Id.in_(ids_list))
              .order_by(Servicio.Nombre)
              .all()
        )

    total_pages = (total + size - 1) // size if size else 1
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(size)
    response.headers["X-Total-Pages"] = str(total_pages)

    return ServicioResponse(Ok=True, Servicios=[ServicioDTO.model_validate(s) for s in items])


# ---------------------------
# Escrituras existentes
# ---------------------------

@router.post(
    "/justificacion",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Guardar justificación del servicio",
)
@router.post(  # alias legacy (OCULTO en Swagger)
    "/set-justificacion",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
def set_justificacion(model: ServicioDTO, db: DbDep):
    from app.services.servicio_service import ServicioService
    ServicioService(db).save_justificacion(model)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{servicio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Patch de campos ambientales y metacampos (server-side)",
)
def patch_servicio(
    servicio_id: Annotated[int, Path(..., ge=1)],
    patch: ServicioPatchDTO,
    db: DbDep,
    request: Request,
):
    # Este endpoint sigue usando compat por header X-User-Id (útil en scripts / pruebas)
    current_user_id = _current_user_id(request)

    srv = db.query(Servicio).filter(Servicio.Id == servicio_id).first()
    if not srv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")

    srv.UpdatedAt = datetime.utcnow()
    srv.ModifiedBy = current_user_id
    srv.Version = (srv.Version or 0) + 1

    for name, value in patch.model_dump(exclude_unset=True).items():
        if name in ("UpdatedAt", "ModifiedBy", "Version") or value is None:
            continue
        setattr(srv, name, value)

    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------
# Diagnóstico
# ---------------------------

@router.get(
    "/{servicio_id}/diagnostico",
    response_model=DiagnosticoDTO,
    summary="Diagnóstico ambiental (RevisionDiagnosticoAmbiental, EtapaSEV)",
)
@router.get(  # alias legacy (OCULTO en Swagger)
    "/get-diagnostico/{servicio_id}",
    response_model=DiagnosticoDTO,
    include_in_schema=False,
)
def get_diagnostico(
    servicio_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
) -> DiagnosticoDTO:
    from app.services.servicio_service import ServicioService
    return ServicioService(db).get_diagnostico(servicio_id)


# ---------------------------
# CRUD ADMIN
# ---------------------------

@router.post(
    "",
    response_model=ServicioDTO,
    status_code=status.HTTP_201_CREATED,
    summary="(ADMIN) Crear servicio",
)
def crear_servicio(
    data: ServicioCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
) -> ServicioDTO:
    from app.services.servicio_service import ServicioService
    srv = ServicioService(db).create(data, created_by=current_user.id)
    return ServicioDTO.model_validate(srv)


@router.put(
    "/{servicio_id}",
    response_model=ServicioDTO,
    summary="(ADMIN) Actualizar servicio",
)
def actualizar_servicio(
    servicio_id: Annotated[int, Path(..., ge=1)],
    data: ServicioUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
) -> ServicioDTO:
    from app.services.servicio_service import ServicioService
    srv = ServicioService(db).update_admin(servicio_id, data, modified_by=current_user.id)
    if not srv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return ServicioDTO.model_validate(srv)


@router.patch(
    "/{servicio_id}/estado",
    response_model=ServicioDTO,
    summary="(ADMIN) Activar/Desactivar servicio (setear Active=true/false)",
)
def set_estado_servicio(
    servicio_id: Annotated[int, Path(..., ge=1)],
    body: ServicioEstadoDTO,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
) -> ServicioDTO:
    from app.services.servicio_service import ServicioService
    srv = ServicioService(db)._set_active(servicio_id, body.Active, modified_by=current_user.id)
    if not srv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return ServicioDTO.model_validate(srv)


@router.patch(
    "/{servicio_id}/reactivar",
    response_model=ServicioDTO,
    summary="(ADMIN) Reactivar servicio (Active=true)",
)
def reactivar_servicio(
    servicio_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
) -> ServicioDTO:
    from app.services.servicio_service import ServicioService
    srv = ServicioService(db).activate(servicio_id, modified_by=current_user.id)
    if not srv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return ServicioDTO.model_validate(srv)


@router.delete(
    "/{servicio_id}",
    response_model=ServicioDTO,
    summary="(ADMIN) Eliminar servicio (soft-delete = Active=false)",
)
def eliminar_servicio(
    servicio_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
) -> ServicioDTO:
    from app.services.servicio_service import ServicioService
    srv = ServicioService(db).soft_delete(servicio_id, modified_by=current_user.id)
    if not srv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return ServicioDTO.model_validate(srv)
