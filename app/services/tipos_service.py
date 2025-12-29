from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from app.db.models.tipo_uso import TipoUso
from app.db.models.tipo_propiedad import TipoPropiedad


class TiposService:
    def list_tipos_uso(self, db: Session) -> List[TipoUso]:
        return db.query(TipoUso).order_by(TipoUso.Nombre, TipoUso.Id).all()

    def list_tipos_propiedad(self, db: Session) -> List[TipoPropiedad]:
        # .NET ordena por Orden
        return db.query(TipoPropiedad).order_by(TipoPropiedad.Orden, TipoPropiedad.Id).all()
