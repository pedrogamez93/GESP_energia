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
from app.core.security import require_roles  # retorna UserPublic

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/api/v1/servicios", tags=["Servicios"])
ADMIN_ROLE_NAME = "ADMINISTRADOR"

def _current_user_id(request: Request) -> str:
    # Se mantiene para endpoints no-ADMIN que ya lo usan
    uid = getattr(request.state, "user_id", None) or request.headers.get("X-User-Id")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="userId no presente")
    return uid

def _is_user_admin(db: Session, user_id: str) -> bool:
    stmt = (
        select(AspNetRole.Name)
        .join(AspNetUserRole, AspNetUserRole.RoleId == AspNetRole.Id)
        .where(AspNetUserRole.UserId == user_id)
        .where(AspNetRole.Name == ADMIN_ROLE_NAME)
        .limit(1)
    )
    return db.execute(stmt).first() is not None

# ---------------------------
# Públicos / Compatibles (ya existentes)
# ---------------------------

@router.get(
    "/institucion/{institucion_id}/usuario/{user_id}",
    response_model=List[ServicioDTO],
    summary="Servicios por institución y usuario (respeta rol ADMINISTRADOR)",
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
    q = db.query(Servicio).filter(Servicio.Active == True, Servicio.InstitucionId == institucion_id)
    if not admin:
        q = q.join(UsuarioServicio, UsuarioServicio.ServicioId == Servicio.Id).filter(UsuarioServicio.UsuarioId == user_id)
    servicios = q.order_by(Servicio.Nombre).all()
    return [ServicioDTO.model_validate(x) for x in servicios]

@router.get(
    "/lista/institucion/{institucion_id}",
    response_model=List[ServicioListDTO],
    summary="Lista ligera de servicios por institución (AllowAnonymous)",
    description="Valida app y devuelve (Id, Nombre) ordenado."
)
@router.get(  # alias legacy (OCULTO en Swagger)
    "/getlist-by-institucionid/{institucion_id}",
    response_model=List[ServicioListDTO],
    include_in_schema=False,
)
def get_list_by_institucionid(
    institucion_id: Annotated[int, Path(..., ge=1)],
    request: Request,
    db: DbDep
) -> List[ServicioListDTO]:
    if not is_app_validate(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    servicios = (
        db.query(Servicio)
          .filter(Servicio.Active == True, Servicio.InstitucionId == institucion_id)
          .order_by(Servicio.Nombre)
          .all()
    )
    return [ServicioListDTO.model_validate(x) for x in servicios]

@router.get(
    "/usuario/{user_id}",
    response_model=ServicioResponse,
    summary="Servicios asociados a un user_id (respeta rol ADMINISTRADOR)",
)
@router.get(  # alias legacy (OCULTO en Swagger)
    "/getByUserId/{user_id}",
    response_model=ServicioResponse,
    include_in_schema=False,
)
def get_by_user_id(
    user_id: Annotated[str, Path(...)],
    db: DbDep
) -> ServicioResponse:
    admin = _is_user_admin(db, user_id)
    q = db.query(Servicio).filter(Servicio.Active == True)
    if not admin:
        q = (
            q.join(UsuarioServicio, UsuarioServicio.ServicioId == Servicio.Id)
             .filter(UsuarioServicio.UsuarioId == user_id)
        )
    servicios = q.order_by(Servicio.Nombre).all()
    return ServicioResponse(Ok=True, Servicios=[ServicioDTO.model_validate(s) for s in servicios])

@router.get(
    "/usuario",
    response_model=ServicioResponse,
    summary="Servicios paginados del usuario autenticado (respeta rol ADMINISTRADOR)",
    description="Lee el user_id de request.state.user_id (o header X-User-Id para pruebas).",
)
@router.get(  # alias legacy (OCULTO en Swagger)
    "/getByUserIdPagin",
    response_model=ServicioResponse,
    include_in_schema=False,
)
def get_by_user_id_pagin(
    response: Response,
    db: DbDep,
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 10,
    InstitucionId: Annotated[int | None, Query()] = None,
    Pmg: Annotated[bool, Query()] = False,
) -> ServicioResponse:
    current_user_id = _current_user_id(request)
    admin = _is_user_admin(db, current_user_id)

    base = db.query(Servicio).filter(Servicio.Active == True)
    if not admin:
        base = (
            base.join(UsuarioServicio, UsuarioServicio.ServicioId == Servicio.Id)
                .filter(UsuarioServicio.UsuarioId == current_user_id)
        )

    if InstitucionId is not None:
        base = base.filter(Servicio.InstitucionId == InstitucionId)

    if Pmg:
        base = base.filter(Servicio.ReportaPMG == True)

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
    srv = db.query(Servicio).filter(Servicio.Id == servicio_id).first()
    if not srv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")

    current_user_id = _current_user_id(request)

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
    db: DbDep
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

# ---- NUEVO: activar/desactivar ----

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

from app.db.models.institucion import Institucion
from app.schemas.institucion import InstitucionListDTO

@router.get(
    "/lista/servicio/{servicio_id}",
    response_model=List[InstitucionListDTO],
    summary="Lista ligera de instituciones por servicio (AllowAnonymous)",
    description="Valida app y devuelve (Id, Nombre) de la(s) institución(es) dueña(s) del servicio."
)
def get_instituciones_by_servicio(
    servicio_id: Annotated[int, Path(..., ge=1)],
    request: Request,
    db: DbDep
) -> List[InstitucionListDTO]:
    # Validación anónima simétrica a /lista/institucion/{institucion_id}
    if not is_app_validate(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    # Join directo Servicio -> Institucion (1 institución por servicio hoy)
    rows = (
        db.query(Institucion.Id, Institucion.Nombre)
          .join(Servicio, Servicio.InstitucionId == Institucion.Id)
          .filter(
              Servicio.Id == servicio_id,
              Servicio.Active == True,
              Institucion.Active == True
          )
          .distinct()
          .order_by(Institucion.Nombre)
          .all()
    )

    # Normaliza a DTO de lista
    return [InstitucionListDTO(Id=r[0], Nombre=r[1]) for r in rows]