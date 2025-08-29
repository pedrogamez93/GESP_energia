from __future__ import annotations
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.reporte_service import ReporteService
from app.schemas.reporte import SerieMensualDTO, ConsumoMedidorDTO, ConsumoNumeroClienteDTO, KPIsDTO

router = APIRouter(prefix="/api/v1/reportes", tags=["Reportes"])
svc = ReporteService()
DbDep = Annotated[Session, Depends(get_db)]

@router.get("/consumo-mensual", response_model=List[SerieMensualDTO])
def consumo_mensual(db: DbDep,
                    DivisionId: int = Query(..., ge=1),
                    EnergeticoId: int = Query(..., ge=1),
                    Desde: str = Query(..., description="YYYY-MM-01"),
                    Hasta: str = Query(..., description="YYYY-MM-01 (exclusivo)")):
    rows = svc.serie_mensual(db, DivisionId, EnergeticoId, Desde, Hasta)
    return [SerieMensualDTO.model_validate(x) for x in rows]

@router.get("/consumo-por-medidor", response_model=List[ConsumoMedidorDTO])
def consumo_por_medidor(db: DbDep,
                        DivisionId: int | None = Query(default=None, ge=1),
                        EnergeticoId: int | None = Query(default=None, ge=1),
                        Desde: str | None = Query(default=None, description="YYYY-MM-DD"),
                        Hasta: str | None = Query(default=None, description="YYYY-MM-DD (exclusivo)")):
    rows = svc.consumo_por_medidor(db, DivisionId, EnergeticoId, Desde, Hasta)
    return [ConsumoMedidorDTO.model_validate(x) for x in rows]

@router.get("/consumo-por-numero-cliente", response_model=List[ConsumoNumeroClienteDTO])
def consumo_por_num_cliente(db: DbDep,
                            DivisionId: int | None = Query(default=None, ge=1),
                            EnergeticoId: int | None = Query(default=None, ge=1),
                            Desde: str | None = Query(default=None),
                            Hasta: str | None = Query(default=None)):
    rows = svc.consumo_por_num_cliente(db, DivisionId, EnergeticoId, Desde, Hasta)
    return [ConsumoNumeroClienteDTO.model_validate(x) for x in rows]

@router.get("/kpis", response_model=KPIsDTO)
def kpis(db: DbDep,
         DivisionId: int | None = Query(default=None, ge=1),
         EnergeticoId: int | None = Query(default=None, ge=1),
         Desde: str | None = Query(default=None),
         Hasta: str | None = Query(default=None)):
    data = svc.kpis(db, DivisionId, EnergeticoId, Desde, Hasta)
    return KPIsDTO.model_validate(data)
