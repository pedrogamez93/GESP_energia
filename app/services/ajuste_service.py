# app/services/ajuste_service.py
from __future__ import annotations

from datetime import datetime
from typing import Dict

from sqlalchemy.orm import Session

from app.db.models.ajuste import Ajuste
from app.schemas.ajustes import AjustePatchDTO


class AjusteService:
    """
    Servicio de banderas de configuración (tabla dbo.Ajustes).
    Garantiza que siempre exista un registro y expone helpers de autorización.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------
    # Creación/obtención del único registro de ajustes
    # ---------------------------
    def _get_or_create(self) -> Ajuste:
        obj = self.db.query(Ajuste).order_by(Ajuste.Id.asc()).first()
        if obj:
            return obj

        now = datetime.utcnow()
        obj = Ajuste(
            CreatedAt=now,
            UpdatedAt=now,
            Version=1,
            Active=True,
            # Flags por defecto: todo deshabilitado salvo Active (ajústalo a tu gusto)
            EditUnidadPMG=False,
            DeleteUnidadPMG=False,
            ComprasServicio=False,
            CreateUnidadPMG=False,
            ActiveAlcanceModule=False,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    # ---------------------------
    # Lectura/actualización
    # ---------------------------
    def get(self) -> Ajuste:
        return self._get_or_create()

    def patch(self, data: AjustePatchDTO) -> Ajuste:
        obj = self._get_or_create()
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        obj.UpdatedAt = datetime.utcnow()
        obj.Version = (obj.Version or 0) + 1
        self.db.commit()
        self.db.refresh(obj)
        return obj

    # ---------------------------
    # Helpers de autorización / features
    # ---------------------------
    def get_flags(self) -> Dict[str, bool]:
        a = self.get()
        return {
            "EditUnidadPMG": bool(a.EditUnidadPMG),
            "DeleteUnidadPMG": bool(a.DeleteUnidadPMG),
            "CreateUnidadPMG": bool(a.CreateUnidadPMG),
            "ComprasServicio": bool(a.ComprasServicio),
            "ActiveAlcanceModule": bool(a.ActiveAlcanceModule),
        }

    def can_edit_unidad_pmg(self) -> bool:
        """Permite editar campos sensibles de Unidad PMG (años, etc.)."""
        return self.get().EditUnidadPMG is True

    def can_delete_unidad_pmg(self) -> bool:
        """Permite eliminar/activar/desactivar Unidad PMG en cascada."""
        return self.get().DeleteUnidadPMG is True

    def can_create_unidad_pmg(self) -> bool:
        """Permite crear nuevas Unidades PMG (si aplica a tu flujo)."""
        return self.get().CreateUnidadPMG is True

    def is_compras_servicio_enabled(self) -> bool:
        """Feature flag de compras por servicio (si tienes endpoints asociados)."""
        return self.get().ComprasServicio is True

    def is_alcance_module_active(self) -> bool:
        """Feature flag de módulo de alcance."""
        return self.get().ActiveAlcanceModule is True
