from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.inmuebles import (
    InmuebleDTO, InmuebleListDTO, InmuebleCreate, InmuebleUpdate,
    InmuebleByAddressRequest, InmuebleUnidadRequest, InmueblePage, UnidadVinculadaDTO
)
from app.services.inmueble_service import InmuebleService
from app.schemas.direcciones import DireccionDTO, DireccionCreate, DireccionUpdate
from app.services.direccion_service import DireccionService
from app.db.models.division import Division
from app.db.models.unidad_inmueble import UnidadInmueble


router = APIRouter(prefix="/api/v1/inmuebles", tags=["Inmuebles"])
DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=InmueblePage, summary="Listado paginado de inmuebles")
def listar_inmuebles(
    db: DbDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    active: Annotated[bool | None, Query()] = True,
    servicio_id: Annotated[int | None, Query()] = None,
    region_id: Annotated[int | None, Query()] = None,
    comuna_id: Annotated[int | None, Query()] = None,
    tipo_inmueble: Annotated[int | None, Query()] = None,
    direccion: Annotated[str | None, Query()] = None,  # Calle/Numero (compat .NET V2)
    search: Annotated[str | None, Query()] = None,     # Nombre/NroRol/DirecciónCompleta
    gev: Annotated[int | None, Query()] = 3,           # default .NET: Active && GeVersion==3
):
    total, items = InmuebleService(db).list_paged(
        page=page, page_size=page_size, active=active,
        servicio_id=servicio_id, region_id=region_id, comuna_id=comuna_id,
        tipo_inmueble=tipo_inmueble, direccion=direccion, search=search, gev=gev
    )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/{inmueble_id}", response_model=InmuebleDTO, summary="Detalle de inmueble (con árbol/pisos/áreas/unidades)")
def obtener_inmueble(inmueble_id: Annotated[int, Path(ge=1)], db: DbDep):
    obj = InmuebleService(db).get(inmueble_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return obj


@router.post("", response_model=InmuebleDTO, status_code=status.HTTP_201_CREATED, summary="(ADMIN) Crear inmueble")
def crear_inmueble(
    data: InmuebleCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return InmuebleService(db).create(data, created_by=current_user.id)


@router.put("/{inmueble_id}", response_model=InmuebleDTO, summary="(ADMIN) Actualizar inmueble")
def actualizar_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    data: InmuebleUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    updated = InmuebleService(db).update(inmueble_id, data, modified_by=current_user.id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return updated


@router.delete("/{inmueble_id}", response_model=InmuebleDTO, summary="(ADMIN) Eliminar inmueble (soft-delete)")
def eliminar_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    deleted = InmuebleService(db).soft_delete(inmueble_id, modified_by=current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return deleted


# Compat .NET V1: búsqueda por dirección exacta
@router.post("/by-address", response_model=List[InmuebleListDTO], summary="Buscar por dirección exacta")
def inmuebles_por_direccion(req: InmuebleByAddressRequest, db: DbDep):
    return InmuebleService(db).get_by_address(req)


# Compat .NET V1: vínculos Unidad <-> Inmueble
@router.post("/{inmueble_id}/unidades", status_code=status.HTTP_204_NO_CONTENT, summary="Vincular unidad a inmueble")
def add_unidad_a_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    body: InmuebleUnidadRequest,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    InmuebleService(db).add_unidad(inmueble_id, body.UnidadId)
    # Se mantiene 204 para compatibilidad .NET V1
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{inmueble_id}/unidades/{unidad_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Desvincular unidad de inmueble")
def remove_unidad_de_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    unidad_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    InmuebleService(db).remove_unidad(inmueble_id, unidad_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Dirección del inmueble
@router.get("/{inmueble_id}/direccion", response_model=DireccionDTO | None, summary="Dirección del inmueble (si existe)")
def obtener_direccion_inmueble(inmueble_id: Annotated[int, Path(ge=1)], db: DbDep):
    d = db.query(Division).filter(Division.Id == inmueble_id).first()
    if not d or not d.DireccionInmuebleId:
        return None
    dir_ = DireccionService(db).get(d.DireccionInmuebleId)
    return DireccionDTO.model_validate(dir_) if dir_ else None


@router.put("/{inmueble_id}/direccion", response_model=DireccionDTO, summary="(ADMIN) Reemplazar/crear dirección del inmueble")
def actualizar_direccion_inmueble(
    inmueble_id: Annotated[int, Path(ge=1)],
    data: DireccionUpdate,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    d = db.query(Division).filter(Division.Id == inmueble_id).first()
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inmueble no encontrado")

    svc = DireccionService(db)
    if d.DireccionInmuebleId:
        upd = svc.update(d.DireccionInmuebleId, data)
        if not upd:
            raise HTTPException(status_code=404, detail="Dirección no encontrada")
        return DireccionDTO.model_validate(upd)
    else:
        created = svc.create(DireccionCreate(**data.model_dump(exclude_unset=True)))
        d.DireccionInmuebleId = created.Id
        db.commit()
        return DireccionDTO.model_validate(created)


@router.get("/{inmueble_id}/unidades", response_model=List[UnidadVinculadaDTO], summary="Unidades vinculadas al inmueble")
def listar_unidades_de_inmueble(inmueble_id: Annotated[int, Path(ge=1)], db: DbDep):
    # Devuelve solo los IDs vinculados (DTO ligero para compatibilidad V1)
    rows = db.query(UnidadInmueble.UnidadId).filter(UnidadInmueble.InmuebleId == inmueble_id).all()
    return [UnidadVinculadaDTO(UnidadId=r[0]) for r in rows]
