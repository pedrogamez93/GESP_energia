# app/api/v1/inmuebles.py
from __future__ import annotations

import logging
from typing import Annotated, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.inmuebles import (
    InmuebleDTO,
    InmuebleListDTO,
    InmuebleCreate,
    InmuebleUpdate,
    InmuebleByAddressRequest,
    InmuebleUnidadRequest,
    InmueblePage,
    UnidadVinculadaDTO,
)
from app.services.inmueble_service import InmuebleService

from app.schemas.direcciones import DireccionDTO, DireccionCreate, DireccionUpdate
from app.services.direccion_service import DireccionService

from app.db.models.division import Division
from app.db.models.unidad_inmueble import UnidadInmueble

# ✅ Scope centralizado
from app.services.inmueble_scope import (
    ensure_actor_can_edit_division,
    ensure_actor_can_touch_unidad,
    ensure_actor_can_create_inmueble_for_servicio,
    is_admin,
)

router = APIRouter(prefix="/api/v1/inmuebles", tags=["Inmuebles"])
DbDep = Annotated[Session, Depends(get_db)]
Log = logging.getLogger(__name__)

# ==========================================================
# ✅ ROLES
#   - LECTURA: incluye GESTOR DE CONSULTA
#   - ESCRITURA: NO incluye GESTOR DE CONSULTA
# ==========================================================
INMUEBLES_READ_ROLES: Tuple[str, ...] = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_SERVICIO",
    "GESTOR_FLOTA",
    "GESTOR DE CONSULTA",
)

INMUEBLES_WRITE_ROLES: Tuple[str, ...] = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_SERVICIO",
    "GESTOR_FLOTA",
)

ReadUserDep = Annotated[UserPublic, Depends(require_roles(*INMUEBLES_READ_ROLES))]
WriteUserDep = Annotated[UserPublic, Depends(require_roles(*INMUEBLES_WRITE_ROLES))]


# ─────────────────────────────────────────────
# GETs (lectura)
# ─────────────────────────────────────────────
@router.get(
    "",
    response_model=InmueblePage,
    summary="Listado paginado de inmuebles",
)
def listar_inmuebles(
    db: DbDep,
    u: ReadUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    active: Annotated[bool | None, Query()] = None,
    servicio_id: Annotated[int | None, Query()] = None,
    region_id: Annotated[int | None, Query()] = None,
    comuna_id: Annotated[int | None, Query()] = None,
    tipo_inmueble: Annotated[int | None, Query()] = None,
    direccion: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    gev: Annotated[int | None, Query()] = 3,
):
    # 🔒 Regla simple: no-admin debe filtrar por algún eje (servicio o comuna o región)
    # (evita “listado global” de inmuebles a gestores/consulta)
    if not is_admin(u) and servicio_id is None and comuna_id is None and region_id is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "missing_filter",
                "msg": "Para tu rol debes filtrar al menos por servicio_id, comuna_id o region_id.",
            },
        )

    total, items = InmuebleService(db).list_paged(
        page=page,
        page_size=page_size,
        active=active,
        servicio_id=servicio_id,
        region_id=region_id,
        comuna_id=comuna_id,
        tipo_inmueble=tipo_inmueble,
        direccion=direccion,
        search=search,
        gev=gev,
    )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get(
    "/{inmueble_id}",
    response_model=InmuebleDTO,
    summary="Detalle de inmueble (con árbol/pisos/áreas/unidades)",
)
def obtener_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    u: ReadUserDep,
):
    # 🔒 inmueble == Division => scope por división
    ensure_actor_can_edit_division(db, u, int(inmueble_id))  # (para lectura sirve igual: valida alcance)

    obj = InmuebleService(db).get(int(inmueble_id))
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return obj


@router.post(
    "/by-address",
    response_model=List[InmuebleListDTO],
    summary="Buscar por dirección exacta",
)
def inmuebles_por_direccion(
    req: InmuebleByAddressRequest,
    db: DbDep,
    u: ReadUserDep,
):
    # Nota: este endpoint puede devolver varios; si tu service no filtra por scope,
    # aquí lo ideal es filtrar por alcance post-query (más caro pero seguro).
    items = InmuebleService(db).get_by_address(req)
    if is_admin(u):
        return items

    filtered: list[InmuebleListDTO] = []
    for it in items:
        div_id = int(getattr(it, "Id", None) or getattr(it, "id", None) or 0)
        if not div_id:
            continue
        try:
            ensure_actor_can_edit_division(db, u, div_id)
            filtered.append(it)
        except HTTPException:
            continue
    return filtered


@router.get(
    "/{inmueble_id}/direccion",
    response_model=DireccionDTO | None,
    summary="Dirección del inmueble (si existe)",
)
def obtener_direccion_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    u: ReadUserDep,
):
    ensure_actor_can_edit_division(db, u, int(inmueble_id))

    d = db.query(Division).filter(Division.Id == int(inmueble_id)).first()
    if not d or not getattr(d, "DireccionInmuebleId", None):
        return None

    dir_ = DireccionService(db).get(int(d.DireccionInmuebleId))
    return DireccionDTO.model_validate(dir_) if dir_ else None


@router.get(
    "/{inmueble_id}/unidades",
    response_model=List[UnidadVinculadaDTO],
    summary="Unidades vinculadas al inmueble",
)
def listar_unidades_de_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    u: ReadUserDep,
):
    ensure_actor_can_edit_division(db, u, int(inmueble_id))

    rows = db.query(UnidadInmueble.UnidadId).filter(UnidadInmueble.InmuebleId == int(inmueble_id)).all()

    # 🔒 extra: valida que las unidades también sean tocables por el actor (si aplica)
    # Para rol consulta/gestor, normalmente sí; si tu scope de unidad es distinto, ajustamos.
    out: list[UnidadVinculadaDTO] = []
    for r in rows:
        uid = int(r[0])
        try:
            ensure_actor_can_touch_unidad(db, u, uid)
            out.append(UnidadVinculadaDTO(UnidadId=uid))
        except HTTPException:
            continue
    return out


@router.get(
    "/por-unidad/{unidad_id}",
    response_model=InmuebleDTO,
)
def get_inmueble_por_unidad(
    unidad_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    u: ReadUserDep,
):
    ensure_actor_can_touch_unidad(db, u, int(unidad_id))

    svc = InmuebleService(db)
    dto = svc.get_by_unidad(int(unidad_id))
    if not dto:
        raise HTTPException(status_code=404, detail="No se encontró inmueble (Division) para la unidad indicada")

    # 🔒 asegura que el inmueble resultante también está dentro de alcance
    div_id = int(getattr(dto, "Id", None) or getattr(dto, "id", None) or 0)
    if div_id:
        ensure_actor_can_edit_division(db, u, div_id)

    return dto


@router.get(
    "/por-unidad/{unidad_id}/lista",
    response_model=List[InmuebleListDTO],
)
def list_inmuebles_por_unidad(
    unidad_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    u: ReadUserDep,
):
    ensure_actor_can_touch_unidad(db, u, int(unidad_id))

    svc = InmuebleService(db)
    items = svc.list_by_unidad(int(unidad_id))
    if is_admin(u):
        return items

    filtered: list[InmuebleListDTO] = []
    for it in items:
        div_id = int(getattr(it, "Id", None) or getattr(it, "id", None) or 0)
        if not div_id:
            continue
        try:
            ensure_actor_can_edit_division(db, u, div_id)
            filtered.append(it)
        except HTTPException:
            continue
    return filtered


# ─────────────────────────────────────────────
# Escrituras (ADMIN + gestores con scope robusto)
# ─────────────────────────────────────────────
@router.post(
    "",
    response_model=InmuebleDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear inmueble (ADMIN | GESTOR_* con scope por Servicio/Institución)",
)
def crear_inmueble(
    data: InmuebleCreate,
    db: DbDep,
    current_user: WriteUserDep,
):
    if is_admin(current_user):
        return InmuebleService(db).create(data, created_by=current_user.id)

    servicio_id = getattr(data, "ServicioId", None)

    # Si no viene ServicioId, intentamos heredarlo del ParentId (como hace el service)
    if servicio_id is None and getattr(data, "ParentId", None):
        parent_row = db.query(Division.ServicioId).filter(Division.Id == int(data.ParentId)).first()
        servicio_id = int(parent_row[0]) if parent_row and parent_row[0] is not None else None

    if servicio_id is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "missing_servicio",
                "msg": "Para crear un inmueble como gestor debes indicar ServicioId o ParentId con ServicioId heredable.",
            },
        )

    ensure_actor_can_create_inmueble_for_servicio(db, current_user, int(servicio_id))
    return InmuebleService(db).create(data, created_by=current_user.id)


@router.put(
    "/{inmueble_id}",
    response_model=InmuebleDTO,
    summary="Actualizar inmueble (ADMIN | GESTOR_* con scope robusto)",
)
def actualizar_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    data: InmuebleUpdate,
    db: DbDep,
    current_user: WriteUserDep,
):
    ensure_actor_can_edit_division(db, current_user, int(inmueble_id))

    updated = InmuebleService(db).update(int(inmueble_id), data, modified_by=current_user.id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return updated


@router.delete(
    "/{inmueble_id}",
    response_model=InmuebleDTO,
    summary="Eliminar inmueble (soft-delete) (ADMIN | GESTOR_* con scope robusto)",
)
def eliminar_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    current_user: WriteUserDep,
):
    ensure_actor_can_edit_division(db, current_user, int(inmueble_id))

    deleted = InmuebleService(db).soft_delete(int(inmueble_id), modified_by=current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return deleted


@router.put(
    "/{inmueble_id}/activar",
    response_model=InmuebleDTO,
    summary="Activar inmueble (ADMIN | GESTOR_* con scope robusto)",
)
def activar_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    current_user: WriteUserDep,
):
    ensure_actor_can_edit_division(db, current_user, int(inmueble_id))

    obj = InmuebleService(db).set_active(int(inmueble_id), True, current_user.id)
    if not obj:
        raise HTTPException(404, "No encontrado")
    return obj


@router.put(
    "/{inmueble_id}/desactivar",
    response_model=InmuebleDTO,
    summary="Desactivar inmueble (ADMIN | GESTOR_* con scope robusto)",
)
def desactivar_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    current_user: WriteUserDep,
):
    ensure_actor_can_edit_division(db, current_user, int(inmueble_id))

    obj = InmuebleService(db).set_active(int(inmueble_id), False, current_user.id)
    if not obj:
        raise HTTPException(404, "No encontrado")
    return obj


@router.put(
    "/{inmueble_id}/direccion",
    response_model=DireccionDTO,
    summary="Reemplazar/crear dirección del inmueble (ADMIN | GESTOR_* con scope robusto)",
)
def actualizar_direccion_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    data: DireccionUpdate,
    db: DbDep,
    current_user: WriteUserDep,
):
    ensure_actor_can_edit_division(db, current_user, int(inmueble_id))

    d = db.query(Division).filter(Division.Id == int(inmueble_id)).first()
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inmueble no encontrado")

    svc_dir = DireccionService(db)
    if getattr(d, "DireccionInmuebleId", None):
        upd = svc_dir.update(int(d.DireccionInmuebleId), data)
        if not upd:
            raise HTTPException(status_code=404, detail="Dirección no encontrada")
        return DireccionDTO.model_validate(upd)
    else:
        created = svc_dir.create(DireccionCreate(**data.model_dump(exclude_unset=True)))
        d.DireccionInmuebleId = created.Id
        db.commit()
        return DireccionDTO.model_validate(created)


@router.post(
    "/{inmueble_id}/unidades",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Vincular unidad a inmueble (ADMIN | GESTOR_* con scope robusto)",
)
def add_unidad_a_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    body: InmuebleUnidadRequest,
    db: DbDep,
    current_user: WriteUserDep,
):
    ensure_actor_can_edit_division(db, current_user, int(inmueble_id))
    ensure_actor_can_touch_unidad(db, current_user, int(body.UnidadId))

    InmuebleService(db).add_unidad(int(inmueble_id), int(body.UnidadId))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{inmueble_id}/unidades/{unidad_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desvincular unidad de inmueble (ADMIN | GESTOR_* con scope robusto)",
)
def remove_unidad_de_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    unidad_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    current_user: WriteUserDep,
):
    ensure_actor_can_edit_division(db, current_user, int(inmueble_id))
    ensure_actor_can_touch_unidad(db, current_user, int(unidad_id))

    InmuebleService(db).remove_unidad(int(inmueble_id), int(unidad_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
