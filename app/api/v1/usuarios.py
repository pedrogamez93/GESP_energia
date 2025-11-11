from typing import Annotated, List
from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.usuario_vinculo import IdsPayload, UserDetailFullDTO
from app.services.usuario_vinculo_service import UsuarioVinculoService

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios (admin)"])
svc = UsuarioVinculoService()
DbDep = Annotated[Session, Depends(get_db)]

# -------- Detalle admin (usuario completo + sets) --------
@router.get(
    "/{user_id}",
    response_model=UserDetailFullDTO,
    summary="Detalle de usuario (ADMIN): datos completos + roles y sets vinculados",
)
def get_user_detail(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    user, roles, inst_ids, srv_ids, div_ids, uni_ids = svc.get_detail(db, user_id)

    # Mapeo 1:1 de la entidad a AspNetUserDTO y añadimos los sets
    base = UserDetailFullDTO.model_validate(user).model_dump()
    base.update({
        "Roles": roles,
        "InstitucionIds": inst_ids,
        "ServicioIds": srv_ids,
        "DivisionIds": div_ids,
        "UnidadIds": uni_ids,
    })
    return UserDetailFullDTO(**base)

# -------- Resto (sin cambios) --------
def _actor_id(current_user: UserPublic | None, request: Request | None) -> str | None:
    return (current_user.id if current_user else None) or (request.headers.get("X-User-Id") if request else None)

@router.put("/{user_id}/instituciones", response_model=List[int], summary="(ADMIN) Reemplaza instituciones vinculadas")
def set_user_instituciones(user_id: Annotated[str, Path(...)], db: DbDep,
                           _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
                           payload: IdsPayload | None = None):
    ids = payload.Ids if payload else []
    return svc.set_instituciones(db, user_id, ids)

@router.put("/{user_id}/servicios", response_model=List[int], summary="(ADMIN) Reemplaza servicios vinculados")
def set_user_servicios(user_id: Annotated[str, Path(...)], db: DbDep,
                       _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
                       payload: IdsPayload | None = None):
    ids = payload.Ids if payload else []
    return svc.set_servicios(db, user_id, ids)

@router.put("/{user_id}/divisiones", response_model=List[int], summary="(ADMIN) Reemplaza divisiones vinculadas")
def set_user_divisiones(user_id: Annotated[str, Path(...)], db: DbDep,
                        _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
                        payload: IdsPayload | None = None):
    ids = payload.Ids if payload else []
    return svc.set_divisiones(db, user_id, ids)

@router.put("/{user_id}/unidades", response_model=List[int], summary="(ADMIN) Reemplaza unidades vinculadas")
def set_user_unidades(user_id: Annotated[str, Path(...)], db: DbDep,
                      _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
                      payload: IdsPayload | None = None):
    ids = payload.Ids if payload else []
    return svc.set_unidades(db, user_id, ids)

@router.put("/{user_id}/activar", response_model=UserDetailFullDTO, summary="(ADMINISTRADOR) Activar usuario (Active = true)")
def activar_usuario(user_id: Annotated[str, Path(...)], db: DbDep, request: Request,
                    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    svc.set_active(db, user_id, True, actor_id=_actor_id(current_user, request))
    user, roles, inst_ids, srv_ids, div_ids, uni_ids = svc.get_detail(db, user_id)
    base = UserDetailFullDTO.model_validate(user).model_dump()
    base.update({"Roles": roles, "InstitucionIds": inst_ids, "ServicioIds": srv_ids,
                 "DivisionIds": div_ids, "UnidadIds": uni_ids})
    return UserDetailFullDTO(**base)

@router.put("/{user_id}/desactivar", response_model=UserDetailFullDTO, summary="(ADMINISTRADOR) Desactivar usuario (Active = false)")
def desactivar_usuario(user_id: Annotated[str, Path(...)], db: DbDep, request: Request,
                       current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    svc.set_active(db, user_id, False, actor_id=_actor_id(current_user, request))
    user, roles, inst_ids, srv_ids, div_ids, uni_ids = svc.get_detail(db, user_id)
    base = UserDetailFullDTO.model_validate(user).model_dump()
    base.update({"Roles": roles, "InstitucionIds": inst_ids, "ServicioIds": srv_ids,
                 "DivisionIds": div_ids, "UnidadIds": uni_ids})
    return UserDetailFullDTO(**base)
