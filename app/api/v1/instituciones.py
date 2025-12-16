# app/api/v1/instituciones.py
from typing import List, Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.institucion_service import InstitucionService
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.institucion import (
    InstitucionListDTO,
    InstitucionDTO,
    InstitucionCreate,
    InstitucionUpdate,
)

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/api/v1/instituciones", tags=["Instituciones"])


# ---------------------------
# Públicos (AllowAnonymous)
# ---------------------------

@router.get(
    "",
    response_model=List[InstitucionListDTO],
    summary="Listar instituciones",
    description="Devuelve las instituciones. Por defecto solo las activas; se puede incluir las inactivas.",
)
def list_instituciones(
    db: DbDep,
    include_inactive: bool = Query(
        False,
        description="Si es true, incluye instituciones con Active = false (devuelve activas + inactivas).",
    ),
) -> List[InstitucionListDTO]:
    return InstitucionService(db).get_all(include_inactive=include_inactive)


@router.get(  # alias “solo activas” por compatibilidad interna (OCULTO en Swagger)
    "/active",
    response_model=List[InstitucionListDTO],
    include_in_schema=False,
)
def list_instituciones_active_alias(db: DbDep) -> List[InstitucionListDTO]:
    return InstitucionService(db).get_all_active()


@router.get(
    "/asociados/{user_id}",
    response_model=List[InstitucionListDTO],
    summary="Listar instituciones según user_id",
    description=(
        "Si el `user_id` corresponde a un usuario con rol **ADMINISTRADOR** ⇒ devuelve **todas** las instituciones activas.\n"
        "Si **no** es admin ⇒ devuelve **solo** las instituciones activas asociadas a ese `user_id`."
    ),
)
@router.get(  # alias legacy para compatibilidad (OCULTO en Swagger)
    "/getAsociadosByUserId/{user_id}",
    response_model=List[InstitucionListDTO],
    include_in_schema=False,
)
def get_asociados_by_user_id(
    user_id: Annotated[str, Path(..., description="Id del usuario (Guid/str de Identity)")],
    db: DbDep,
) -> List[InstitucionListDTO]:
    return InstitucionService(db).get_by_user_id(user_id)


# ---------------------------
# CRUD (solo ADMINISTRADOR)
# ---------------------------

@router.post(
    "",
    response_model=InstitucionDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear institución (solo ADMINISTRADOR)",
)
def crear_institucion(
    data: InstitucionCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
) -> InstitucionDTO:
    return InstitucionService(db).create(data, created_by=current_user.id)


@router.get(
    "/{institucion_id}",
    response_model=InstitucionDTO,
    summary="Obtener institución por Id (solo ADMINISTRADOR)",
)
def obtener_institucion(
    institucion_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
) -> InstitucionDTO:
    inst = InstitucionService(db).get_by_id(institucion_id)
    return InstitucionDTO.model_validate(inst)


@router.put(
    "/{institucion_id}",
    response_model=InstitucionDTO,
    summary="Actualizar institución (solo ADMINISTRADOR)",
)
def actualizar_institucion(
    institucion_id: Annotated[int, Path(..., ge=1)],
    data: InstitucionUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
) -> InstitucionDTO:
    return InstitucionService(db).update(institucion_id, data, modified_by=current_user.id)


@router.delete(
    "/{institucion_id}",
    response_model=InstitucionDTO,
    summary="Eliminar (soft-delete) institución (solo ADMINISTRADOR)",
    description="Marca la institución como Inactiva (Active = false).",
)
def eliminar_institucion(
    institucion_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
) -> InstitucionDTO:
    return InstitucionService(db).soft_delete(institucion_id, modified_by=current_user.id)


@router.patch(
    "/{institucion_id}/reactivar",
    response_model=InstitucionDTO,
    summary="Reactivar institución (solo ADMINISTRADOR)",
)
def reactivar_institucion(
    institucion_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
) -> InstitucionDTO:
    return InstitucionService(db).reactivate(institucion_id, modified_by=current_user.id)
