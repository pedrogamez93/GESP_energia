# app/api/v1/sistemas_mantenedores.py
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.sistemas_mantenedores import (
    RefrigeracionCatalogosDTO,
    ACSCatalogosDTO,
    EquipoRefrigeracionCreate,
    EquipoRefrigeracionUpdate,
    EquipoACSCreate,
    EquipoACSUpdate,
    CompatEnergeticoCreate,
    SimpleCatalogDTO,
    CompatEquipoEnergeticoDTO,
)
from app.services.sistemas_mantenedores_service import SistemasMantenedoresService


DbDep = Annotated[Session, Depends(get_db)]
# Cualquier usuario autenticado
CurrentUser = Annotated[UserPublic, Depends(require_roles())]
# Solo ADMIN para crear/editar/borrar
CurrentAdmin = Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]

router = APIRouter(
    prefix="/api/v1/sistemas",
    tags=["Sistemas - mantenedores"],
)

# ----------------------------------------------------------------------
# Lectura de catálogos (cualquier usuario logueado)
# ----------------------------------------------------------------------


@router.get(
    "/refrigeracion/catalogos",
    response_model=RefrigeracionCatalogosDTO,
    summary="Catálogos para el mantenedor de Sistema de Refrigeración",
    description=(
        "Devuelve equipos de refrigeración (catálogo base) con sus "
        "energéticos compatibles y la lista fija de temperaturas de seteo (22, 23, 24)."
    ),
)
def get_refrigeracion_catalogos(
    db: DbDep,
    current_user: CurrentUser,
) -> RefrigeracionCatalogosDTO:
    svc = SistemasMantenedoresService(db)
    data = svc.catalogos_refrigeracion()
    return RefrigeracionCatalogosDTO.model_validate(data)


@router.get(
    "/acs/catalogos",
    response_model=ACSCatalogosDTO,
    summary="Catálogos para el mantenedor de Agua Caliente Sanitaria (ACS)",
    description=(
        "Devuelve equipos de ACS (catálogo base) con sus energéticos compatibles "
        "y tipos de colectores solares."
    ),
)
def get_acs_catalogos(
    db: DbDep,
    current_user: CurrentUser,
) -> ACSCatalogosDTO:
    svc = SistemasMantenedoresService(db)
    data = svc.catalogos_acs()
    return ACSCatalogosDTO.model_validate(data)


# ----------------------------------------------------------------------
# CRUD equipos de Refrigeración (solo ADMIN)
# ----------------------------------------------------------------------


@router.post(
    "/refrigeracion/equipos",
    response_model=SimpleCatalogDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear equipo de refrigeración",
)
def crear_equipo_refrigeracion(
    payload: EquipoRefrigeracionCreate,
    db: DbDep,
    current_user: CurrentAdmin,
) -> SimpleCatalogDTO:
    svc = SistemasMantenedoresService(db)
    eq = svc.crear_equipo_refrigeracion(payload.model_dump())
    return SimpleCatalogDTO.model_validate(eq)


@router.put(
    "/refrigeracion/equipos/{equipo_id}",
    response_model=SimpleCatalogDTO,
    summary="Actualizar equipo de refrigeración",
)
def actualizar_equipo_refrigeracion(
    equipo_id: Annotated[int, Path(..., ge=1)],
    payload: EquipoRefrigeracionUpdate,
    db: DbDep,
    current_user: CurrentAdmin,
) -> SimpleCatalogDTO:
    svc = SistemasMantenedoresService(db)
    eq = svc.actualizar_equipo_refrigeracion(
        equipo_id,
        payload.model_dump(exclude_unset=True),
    )
    return SimpleCatalogDTO.model_validate(eq)


@router.delete(
    "/refrigeracion/equipos/{equipo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar equipo de refrigeración",
)
def eliminar_equipo_refrigeracion(
    equipo_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: CurrentAdmin,
) -> None:
    SistemasMantenedoresService(db).eliminar_equipo_refrigeracion(equipo_id)
    return None


# ----------------------------------------------------------------------
# CRUD equipos de ACS (solo ADMIN)
# ----------------------------------------------------------------------


@router.post(
    "/acs/equipos",
    response_model=SimpleCatalogDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear equipo de ACS",
)
def crear_equipo_acs(
    payload: EquipoACSCreate,
    db: DbDep,
    current_user: CurrentAdmin,
) -> SimpleCatalogDTO:
    svc = SistemasMantenedoresService(db)
    eq = svc.crear_equipo_acs(payload.model_dump())
    return SimpleCatalogDTO.model_validate(eq)


@router.put(
    "/acs/equipos/{equipo_id}",
    response_model=SimpleCatalogDTO,
    summary="Actualizar equipo de ACS",
)
def actualizar_equipo_acs(
    equipo_id: Annotated[int, Path(..., ge=1)],
    payload: EquipoACSUpdate,
    db: DbDep,
    current_user: CurrentAdmin,
) -> SimpleCatalogDTO:
    svc = SistemasMantenedoresService(db)
    eq = svc.actualizar_equipo_acs(
        equipo_id,
        payload.model_dump(exclude_unset=True),
    )
    return SimpleCatalogDTO.model_validate(eq)


@router.delete(
    "/acs/equipos/{equipo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar equipo de ACS",
)
def eliminar_equipo_acs(
    equipo_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: CurrentAdmin,
) -> None:
    SistemasMantenedoresService(db).eliminar_equipo_acs(equipo_id)
    return None


# ----------------------------------------------------------------------
# CRUD compatibilidades equipo ↔ energético (solo ADMIN)
# ----------------------------------------------------------------------


@router.post(
    "/equipos/compat",
    response_model=CompatEquipoEnergeticoDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar compatibilidad equipo ↔ energético",
    description=(
        "Crea una relación entre un TipoEquipoCalefaccion y un Energetico. "
        "Se usa tanto para Refrigeración como para ACS."
    ),
)
def crear_compatibilidad_equipo_energetico(
    payload: CompatEnergeticoCreate,
    db: DbDep,
    current_user: CurrentAdmin,
) -> CompatEquipoEnergeticoDTO:
    svc = SistemasMantenedoresService(db)
    rel = svc.crear_compatibilidad(payload.model_dump())
    return CompatEquipoEnergeticoDTO.model_validate(rel)


@router.delete(
    "/equipos/compat/{rel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar compatibilidad equipo ↔ energético",
)
def eliminar_compatibilidad_equipo_energetico(
    rel_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: CurrentAdmin,
) -> None:
    SistemasMantenedoresService(db).eliminar_compatibilidad(rel_id)
    return None
