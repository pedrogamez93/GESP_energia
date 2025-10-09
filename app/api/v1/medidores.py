from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.medidor import (
    MedidorDTO,
    MedidorListDTO,
    MedidorCreate,
    MedidorUpdate,
    MedidorPage,  # tipado de página
)
from app.services.medidor_service import MedidorService

router = APIRouter(prefix="/api/v1/medidores", tags=["Medidores"])
svc = MedidorService()
DbDep = Annotated[Session, Depends(get_db)]


# ---------------- GET públicos ----------------

@router.get("", response_model=MedidorPage, summary="Listado paginado de medidores")
def list_medidores(
    db: DbDep,
    q: str | None = Query(default=None, description="Busca por Número / Nombre cliente"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    NumeroClienteId: int | None = Query(default=None),
    DivisionId: int | None = Query(default=None),
):
    """
    Retorna una página tipada para documentación y validación.
    El servicio debe devolver un dict con:
      { total, page, page_size, items }
    donde items es una lista de instancias ORM o dicts compatibles.
    """
    return svc.list(db, q, page, page_size, NumeroClienteId, DivisionId)


@router.get(
    "/division/{division_id}",
    response_model=List[MedidorListDTO],
    summary="Medidores por división",
)
def list_by_division(
    db: DbDep,
    division_id: Annotated[int, Path(..., ge=1)],
):
    items = svc.by_division(db, division_id)
    # Pydantic v2 permite devolver ORM directamente, pero
    # mantenemos la validación explícita para homogeneidad.
    return [MedidorListDTO.model_validate(x) for x in items]


@router.get(
    "/numero-cliente/{numero_cliente_id}",
    response_model=List[MedidorListDTO],
    summary="Medidores por NúmeroClienteId",
)
def list_by_numero_cliente(
    db: DbDep,
    numero_cliente_id: Annotated[int, Path(..., ge=1)],
):
    items = svc.by_numero_cliente(db, numero_cliente_id)
    return [MedidorListDTO.model_validate(x) for x in items]


@router.get("/{medidor_id}", response_model=MedidorDTO, summary="Detalle de un medidor")
def get_medidor(
    db: DbDep,
    medidor_id: Annotated[int, Path(..., ge=1)],
):
    """
    🔧 Arregla el 500: el schema ahora espera datetime (no str) en CreatedAt/UpdatedAt.
    Con model_config.from_attributes=True, podemos retornar el objeto ORM directo.
    """
    obj = svc.get(db, medidor_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Medidor no encontrado")
    return obj


# --- Buscar por NumeroClienteId + NumMedidor (igual al .NET) ---
@router.get(
    "/buscar",
    response_model=MedidorDTO,
    summary="Buscar por NumeroClienteId y NumMedidor",
)
def find_by_num_cliente_and_numero(
    db: DbDep,
    numeroClienteId: int = Query(..., ge=1),
    numMedidor: str = Query(..., min_length=1),
):
    obj = svc.by_numcliente_and_numero(db, numeroClienteId, numMedidor)
    if not obj:
        raise HTTPException(status_code=404, detail="Medidor no encontrado")
    return obj


# --- Compatibilidad .NET para compras ---
@router.get(
    "/para-compra/by-num-cliente/{num_cliente_id}/by-division/{division_id}",
    response_model=List[MedidorListDTO],
    summary="Medidores habilitados para compra por (NumeroClienteId, DivisionId)",
)
def for_compra(
    db: DbDep,
    num_cliente_id: Annotated[int, Path(..., ge=1)],
    division_id: Annotated[int, Path(..., ge=1)],
):
    items = svc.for_compra_by_numcliente_division(db, num_cliente_id, division_id)
    return [MedidorListDTO.model_validate(x) for x in items]


@router.get(
    "/by-compra/{compra_id}",
    response_model=List[MedidorListDTO],
    summary="Medidores asociados a una compra",
)
def by_compra(
    db: DbDep,
    compra_id: Annotated[int, Path(..., ge=1)],
):
    items = svc.by_compra(db, compra_id)
    return [MedidorListDTO.model_validate(x) for x in items]


@router.post(
    "/check-exist-medidor",
    response_model=MedidorDTO,
    summary="Verifica existencia por (NumeroClienteId, Numero [, DivisionId])",
)
def check_exist_medidor(
    db: DbDep,
    payload: dict,
):
    # Sanitizado básico
    try:
        numero_cliente_id = int(payload.get("NumeroClienteId"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="NumeroClienteId inválido")

    numero = str(payload.get("Numero", "")).strip()
    division_val = payload.get("DivisionId")
    division_id = int(division_val) if division_val is not None else None

    found = svc.check_exist(db, numero_cliente_id, numero, division_id)
    if not found:
        raise HTTPException(status_code=404, detail="No existe el medidor con esos parámetros")
    return found


# ---------------- Escrituras (ADMINISTRADOR) ----------------

@router.post(
    "",
    response_model=MedidorDTO,
    status_code=status.HTTP_201_CREATED,
    summary="(ADMINISTRADOR) Crear medidor",
)
def create_medidor(
    db: DbDep,
    payload: MedidorCreate,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.create(db, payload, created_by=current_user.id)


@router.put(
    "/{medidor_id}",
    response_model=MedidorDTO,
    summary="(ADMINISTRADOR) Actualizar medidor",
)
def update_medidor(
    db: DbDep,
    medidor_id: Annotated[int, Path(..., ge=1)],
    payload: MedidorUpdate,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.update(db, medidor_id, payload, modified_by=current_user.id)


@router.delete(
    "/{medidor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="(ADMINISTRADOR) Eliminar medidor (hard delete)",
)
def delete_medidor(
    db: DbDep,
    medidor_id: Annotated[int, Path(..., ge=1)],
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, medidor_id)
    return None


@router.put(
    "/{medidor_id}/divisiones",
    response_model=List[int],
    summary="(ADMINISTRADOR) Reemplaza divisiones asociadas al medidor (tabla puente)",
)
def set_divisiones(
    db: DbDep,
    medidor_id: Annotated[int, Path(..., ge=1)],
    division_ids: List[int],
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.set_divisiones(db, medidor_id, division_ids, actor_id=current_user.id)
