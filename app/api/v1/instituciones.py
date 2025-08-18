# app/api/v1/instituciones.py
from typing import List, Annotated
from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.institucion_service import InstitucionService
from app.core.security import require_roles

# Schemas
from app.schemas.institucion import (
    InstitucionListDTO,
    InstitucionDTO,
    InstitucionCreate,
    InstitucionUpdate,
)

# Alias de dependencia (NO repetir = Depends(get_db) al usarlo)
DbDep = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/api/v1/instituciones", tags=["Instituciones"])

# ---------------------------
# Públicos (equivalente a AllowAnonymous en .NET)
# ---------------------------

@router.get(
    "",
    response_model=List[InstitucionListDTO],
    summary="Listar instituciones activas",
    description="Devuelve todas las instituciones activas, ordenadas por Nombre.",
)
def get_list_all(db: DbDep) -> List[InstitucionListDTO]:
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
@router.get(  # alias legacy para compatibilidad
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
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def crear_institucion(data: InstitucionCreate, db: DbDep) -> InstitucionDTO:
    return InstitucionService(db).create(data)


@router.get(
    "/{institucion_id}",
    response_model=InstitucionDTO,
    summary="Obtener institución por Id (solo ADMINISTRADOR)",
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def obtener_institucion(
    institucion_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
) -> InstitucionDTO:
    inst = InstitucionService(db).get_by_id(institucion_id)
    return InstitucionDTO.model_validate(inst)


@router.put(
    "/{institucion_id}",
    response_model=InstitucionDTO,
    summary="Actualizar institución (solo ADMINISTRADOR)",
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def actualizar_institucion(
    institucion_id: Annotated[int, Path(..., ge=1)],
    data: InstitucionUpdate,
    db: DbDep,
) -> InstitucionDTO:
    return InstitucionService(db).update(institucion_id, data)


@router.delete(
    "/{institucion_id}",
    response_model=InstitucionDTO,
    summary="Eliminar (soft-delete) institución (solo ADMINISTRADOR)",
    description="Marca la institución como Inactiva (Active = false).",
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def eliminar_institucion(
    institucion_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
) -> InstitucionDTO:
    return InstitucionService(db).soft_delete(institucion_id)


@router.patch(
    "/{institucion_id}/reactivar",
    response_model=InstitucionDTO,
    summary="Reactivar institución (solo ADMINISTRADOR)",
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def reactivar_institucion(
    institucion_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
) -> InstitucionDTO:
    return InstitucionService(db).reactivate(institucion_id)
