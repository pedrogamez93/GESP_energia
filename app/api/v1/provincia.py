from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.provincias import ProvinciaDTO

router = APIRouter(prefix="/api/v1/provincias", tags=["Provincias"])

@router.get("", response_model=list[ProvinciaDTO])
def listar_por_region(
    regionId: int = Query(..., alias="regionId", description="Id de la región"),
    db: Session = Depends(get_db),
):
    try:
        sql = text("""
            SELECT [Id], [RegionId], [Nombre]
            FROM dbo.[Provincias] WITH (NOLOCK)
            WHERE [RegionId] = :region_id
            ORDER BY [Nombre], [Id]
        """)
        rows = db.execute(sql, {"region_id": regionId}).mappings().all()
        return [ProvinciaDTO(**dict(r)) for r in rows]
    except Exception as ex:
        raise HTTPException(status_code=500, detail="Error al obtener provincias") from ex
