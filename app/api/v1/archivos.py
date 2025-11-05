# app/api/routes/archivos.py
from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.archivos import TipoArchivoDTO
from app.services.archivo_adjunto_service import ArchivoAdjuntoService, get_ext_permitidas_factura

router = APIRouter(prefix="/api/v1/archivos", tags=["Archivos adjuntos"])
svc = ArchivoAdjuntoService()

@router.get("/facturas/ext-permitidas", response_model=List[TipoArchivoDTO])
def ext_permitidas(db: Session = Depends(get_db)):
    return get_ext_permitidas_factura(db)

@router.post("/facturas/division/{division_id}")
def add_factura(
    division_id: int,
    archivo: UploadFile = File(...),
    compraId: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    new_id = svc.add_for_compra(db, division_id, compraId, archivo)
    db.commit()
    return {"success": True, "newId": new_id}

@router.put("/facturas/{archivo_id}/division/{division_id}")
def replace_factura(
    archivo_id: int,
    division_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    svc.replace(db, archivo_id, division_id, archivo)
    db.commit()
    return {"success": True}

@router.get("/facturas/{factura_id}")
def download_factura(factura_id: int, db: Session = Depends(get_db)):
    data, mime, nombre = svc.get_by_factura_id(db, factura_id)

    # filename “seguro” para header
    safe_name = nombre.replace('"', '').replace('\n', '').replace('\r', '')
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'}
    )
