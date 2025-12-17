# app/services/division_sistemas_service.py
from __future__ import annotations

import logging
from app.db.models.division import Division
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session


from app.db.models.tipo_luminaria import TipoLuminaria
from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.db.models.tipo_equipo_calefaccion_energetico import TipoEquipoCalefaccionEnergetico
from app.db.models.energetico import Energetico
from app.db.models.tipo_colector import TipoColector  

from app.schemas.division_sistemas import DivisionSistemasDTO, DivisionSistemasUpdate
from app.services.division_service import DivisionService

log = logging.getLogger("division_sistemas")

def _now():
    return datetime.utcnow()



# Campos de sistemas que vamos a exponer/editar
_SYSTEM_FIELDS = {
    # Iluminación
    "TipoLuminariaId",
    # Calefacción
    "EquipoCalefaccionId",
    "EnergeticoCalefaccionId",
    "TempSeteoCalefaccionId",
    # Refrigeración
    "EquipoRefrigeracionId",
    "EnergeticoRefrigeracionId",
    "TempSeteoRefrigeracionId",
    # ACS
    "EquipoAcsId",
    "EnergeticoAcsId",
    "SistemaSolarTermico",
    "ColectorId",
    "SupColectores",
    "FotoTecho",
    "SupFotoTecho",
    # Fotovoltaico
    "InstTerSisFv",
    "SupInstTerSisFv",
    "ImpSisFv",
    "SupImptSisFv",
    "PotIns",
    # Mantenciones
    "MantColectores",
    "MantSfv",
}


class DivisionSistemasService:
    """
    Lógica del mantenedor de sistemas por División:
    - Iluminación (TipoLuminariaId)
    - Calefacción (EquipoCalefaccion*, EnergeticoCalefaccion*, TempSeteoCalefaccionId)
    - Refrigeración (EquipoRefrigeracion*, EnergeticoRefrigeracion*, TempSeteoRefrigeracionId)
    - ACS (EquipoAcs*, EnergeticoAcsId, SistemaSolarTermico, ColectorId, SupColectores,
           FotoTecho, SupFotoTecho, MantColectores)
    - Fotovoltaico (InstTerSisFv, SupInstTerSisFv, ImpSisFv, SupImptSisFv, PotIns, MantSfv)
    """

    def __init__(self) -> None:
        # Reutilizamos la lógica de DivisionService.get (normalización de Pisos, etc.)
        self._division_svc = DivisionService()

    # ------------------------------------------------------------------ #
    # GET de la División (objeto ORM)
    # ------------------------------------------------------------------ #
    def get(self, db: Session, division_id: int) -> Division:
        """
        Devuelve la entidad Division usando la lógica actual de DivisionService.
        """
        return self._division_svc.get(db, division_id)

    # ------------------------------------------------------------------ #
    # Mapear Division -> dict compatible con DivisionSistemasDTO
    # ------------------------------------------------------------------ #
    def to_dto(self, d: Division) -> Dict[str, Any]:
        """
        Convierte la entidad Division a un dict compatible con DivisionSistemasDTO.
        Usa getattr para no romper si faltara algún campo en el modelo.
        """
        data: Dict[str, Any] = {
            "DivisionId": getattr(d, "Id", None),
        }

        for field in _SYSTEM_FIELDS:
            data[field] = getattr(d, field, None)

        data["Version"] = getattr(d, "Version", None)
        return data

    # ------------------------------------------------------------------ #
    # UPDATE parcial de los campos de sistemas
    # ------------------------------------------------------------------ #
    def update(
        self,
        db: Session,
        division_id: int,
        payload: Dict[str, Any],
        user: Optional[str] = None,
    ) -> Division:
        """
        Actualiza solo los campos de sistemas definidos en _SYSTEM_FIELDS.
        `payload` ya viene filtrado con exclude_unset=True desde el router.
        """
        d = self.get(db, division_id)

        for k, v in payload.items():
            if k in _SYSTEM_FIELDS:
                if hasattr(d, k):
                    setattr(d, k, v)
                else:
                    log.debug(
                        "DivisionSistemas.update: campo %r permitido pero no existe en modelo Division",
                        k,
                    )
            else:
                # Ignoramos silenciosamente claves fuera de _SYSTEM_FIELDS
                log.debug("DivisionSistemas.update: ignorando campo no permitido %r", k)

        now = _now()
        if hasattr(d, "UpdatedAt"):
            d.UpdatedAt = now
        if hasattr(d, "Version"):
            d.Version = (d.Version or 0) + 1
        if user and hasattr(d, "ModifiedBy"):
            d.ModifiedBy = user

        db.commit()
        db.refresh(d)
        return d

    # ------------------------------------------------------------------ #
    # Catálogos para combos en la UI
    # ------------------------------------------------------------------ #
    def catalogs(self, db: Session) -> Dict[str, Any]:
        """
        Devuelve todos los catálogos que necesita el front para armar el mantenedor:

        - tiposLuminarias
        - tiposEquiposCalefaccion (mismo catálogo para calefacción, refrigeración y ACS;
          en el front se puede filtrar por código si lo necesitan: CAL / FR / ACS, etc.)
        - energeticos
        - tiposColectores
        - compatibilidadesEquiposEnergeticos: lista de relaciones Equipo ↔ Energético
        """

        # Luminarias
        luminarias: List[TipoLuminaria] = (
            db.query(TipoLuminaria)
            .order_by(TipoLuminaria.Nombre, TipoLuminaria.Id)
            .all()
        )

        # Equipos de calefacción/refrigeración/ACS (mismo catálogo)
        equipos: List[TipoEquipoCalefaccion] = (
            db.query(TipoEquipoCalefaccion)
            .order_by(TipoEquipoCalefaccion.Nombre, TipoEquipoCalefaccion.Id)
            .all()
        )

        # Energéticos
        energeticos: List[Energetico] = (
            db.query(Energetico)
            .order_by(Energetico.Nombre, Energetico.Id)
            .all()
        )

        # Colectores (ACS / FV térmico, etc.)
        colectores: List[TipoColector] = (
            db.query(TipoColector)
            .order_by(TipoColector.Nombre, TipoColector.Id)
            .all()
        )

        # Relación Equipo ↔ Energético
        rels: List[TipoEquipoCalefaccionEnergetico] = (
            db.query(TipoEquipoCalefaccionEnergetico)
            .order_by(
                TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId,
                TipoEquipoCalefaccionEnergetico.EnergeticoId,
            )
            .all()
        )

        def _simple(obj: Any, extra_fields: Optional[List[str]] = None) -> Dict[str, Any]:
            """
            Convierte una entidad simple en un dict con al menos Id y Nombre.
            Si el modelo tiene Active u otros campos extra (Codigo, Tipo, etc.),
            se agregan solo si existen en el modelo (para no romper la BD).
            """
            data: Dict[str, Any] = {
                "Id": getattr(obj, "Id", None),
                "Nombre": getattr(obj, "Nombre", None),
            }

            # Active solo si existe en el modelo (evita errores si la columna no está en la tabla)
            if hasattr(obj.__class__, "Active"):
                # OJO: esto NO fuerza carga desde DB si ya vino en la query;
                # pero si el modelo no tiene columna Active, ni siquiera lo intentamos.
                data["Active"] = getattr(obj, "Active", None)

            if extra_fields:
                for f in extra_fields:
                    if hasattr(obj.__class__, f):
                        data[f] = getattr(obj, f, None)

            return data

        return {
            "tiposLuminarias": [_simple(l) for l in luminarias],
            "tiposEquiposCalefaccion": [
                # Si tu modelo tiene columna Codigo/Tipo, la exponemos:
                _simple(e, extra_fields=["Codigo", "Tipo"])
                for e in equipos
            ],
            "energeticos": [_simple(en) for en in energeticos],
            "tiposColectores": [_simple(c, extra_fields=["Tipo"]) for c in colectores],
            "compatibilidadesEquiposEnergeticos": [
                {
                    "Id": r.Id,
                    "TipoEquipoCalefaccionId": r.TipoEquipoCalefaccionId,
                    "EnergeticoId": r.EnergeticoId,
                }
                for r in rels
            ],
        }


    # ------------------------------------------------------------------ #
    # Catálogos específicos para mantenedores (Refrigeración y ACS)
    # ------------------------------------------------------------------ #
    def refrigeracion_catalogos(self, db: Session) -> Dict[str, Any]:
        """
        Catálogos para el mantenedor de Sistema de Refrigeración.
        - Equipos de refrigeración (TipoEquipoCalefaccion.Tipo == 'FR')
        - Energéticos compatibles por equipo (tabla puente)
        - Temperaturas de seteo fijas (22, 23, 24)
        """
        # 1) Equipos marcados como FR (frío)
        equipos_fr: List[TipoEquipoCalefaccion] = (
            db.query(TipoEquipoCalefaccion)
            .filter(
                getattr(TipoEquipoCalefaccion, "Tipo") == "FR"
            )
            .order_by(TipoEquipoCalefaccion.Nombre, TipoEquipoCalefaccion.Id)
            .all()
        )

        # 2) Energéticos (los usamos para armar diccionario por Id)
        energeticos: List[Energetico] = (
            db.query(Energetico)
            .order_by(Energetico.Nombre, Energetico.Id)
            .all()
        )
        energetico_by_id: Dict[int, Dict[str, Any]] = {
            e.Id: {"id": e.Id, "nombre": e.Nombre}
            for e in energeticos
        }

        # 3) Relaciones Equipo ↔ Energético solo para equipos FR
        ids_equipos_fr = [e.Id for e in equipos_fr] or [-1]
        rels: List[TipoEquipoCalefaccionEnergetico] = (
            db.query(TipoEquipoCalefaccionEnergetico)
            .filter(
                TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId.in_(ids_equipos_fr)
            )
            .order_by(
                TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId,
                TipoEquipoCalefaccionEnergetico.EnergeticoId,
            )
            .all()
        )

        # 4) Armamos salida: cada equipo con su lista de energéticos
        equipos_out: List[Dict[str, Any]] = []
        for eq in equipos_fr:
            eq_rels = [
                r for r in rels
                if r.TipoEquipoCalefaccionId == eq.Id
            ]
            eq_energeticos = [
                energetico_by_id[r.EnergeticoId]
                for r in eq_rels
                if r.EnergeticoId in energetico_by_id
            ]

            equipos_out.append(
                {
                    "id": eq.Id,
                    "nombre": eq.Nombre,
                    "tipo": getattr(eq, "Tipo", None),
                    "active": getattr(eq, "Active", None),
                    "energeticos": eq_energeticos,
                }
            )

        # Temperaturas de seteo: fijas (las que ya usas en el sistema viejo)
        temperaturas_seteo = [22, 23, 24]

        return {
            "equipos": equipos_out,
            "temperaturasSeteo": temperaturas_seteo,
        }

    def acs_catalogos(self, db: Session) -> Dict[str, Any]:
        """
        Catálogos para el mantenedor de Agua Caliente Sanitaria (ACS).
        - Equipos ACS (TipoEquipoCalefaccion.Tipo == 'AC')
        - Energéticos compatibles por equipo
        - Tipos de colectores solares (TipoColector)
        """
        # 1) Equipos marcados como AC (ACS)
        equipos_ac: List[TipoEquipoCalefaccion] = (
            db.query(TipoEquipoCalefaccion)
            .filter(
                getattr(TipoEquipoCalefaccion, "Tipo") == "AC"
            )
            .order_by(TipoEquipoCalefaccion.Nombre, TipoEquipoCalefaccion.Id)
            .all()
        )

        # 2) Energéticos
        energeticos: List[Energetico] = (
            db.query(Energetico)
            .order_by(Energetico.Nombre, Energetico.Id)
            .all()
        )
        energetico_by_id: Dict[int, Dict[str, Any]] = {
            e.Id: {"id": e.Id, "nombre": e.Nombre}
            for e in energeticos
        }

        # 3) Relaciones Equipo ↔ Energético solo para equipos AC
        ids_equipos_ac = [e.Id for e in equipos_ac] or [-1]
        rels: List[TipoEquipoCalefaccionEnergetico] = (
            db.query(TipoEquipoCalefaccionEnergetico)
            .filter(
                TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId.in_(ids_equipos_ac)
            )
            .order_by(
                TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId,
                TipoEquipoCalefaccionEnergetico.EnergeticoId,
            )
            .all()
        )

        equipos_out: List[Dict[str, Any]] = []
        for eq in equipos_ac:
            eq_rels = [
                r for r in rels
                if r.TipoEquipoCalefaccionId == eq.Id
            ]
            eq_energeticos = [
                energetico_by_id[r.EnergeticoId]
                for r in eq_rels
                if r.EnergeticoId in energetico_by_id
            ]

            equipos_out.append(
                {
                    "id": eq.Id,
                    "nombre": eq.Nombre,
                    "tipo": getattr(eq, "Tipo", None),
                    "active": getattr(eq, "Active", None),
                    "energeticos": eq_energeticos,
                }
            )

        # 4) Colectores solares térmicos
        colectores: List[TipoColector] = (
            db.query(TipoColector)
            .order_by(TipoColector.Nombre, TipoColector.Id)
            .all()
        )
        colectores_out = [
            {
                "id": c.Id,
                "nombre": c.Nombre,
                "tipo": getattr(c, "Tipo", None),
                "active": getattr(c, "Active", None),
            }
            for c in colectores
        ]

        return {
            "equipos": equipos_out,
            "colectores": colectores_out,
        }

    # ------------------------------------------------------------------ #
    # GET/PUT por secciones (detalle)
    # ------------------------------------------------------------------ #

    # Campos por sección (deben coincidir con nombres en BD/modelo y con los DTOs)
    _ILUMINACION_FIELDS = {
        "TipoLuminariaId",
    }

    _CALEFACCION_FIELDS = {
        "EquipoCalefaccionId",
        "EnergeticoCalefaccionId",
        "TempSeteoCalefaccionId",
    }

    _REFRIGERACION_FIELDS = {
        "EquipoRefrigeracionId",
        "EnergeticoRefrigeracionId",
        "TempSeteoRefrigeracionId",
    }

    _ACS_FIELDS = {
        "EquipoAcsId",
        "EnergeticoAcsId",
        "SistemaSolarTermico",
        "ColectorId",
        "SupColectores",
        "FotoTecho",
        "SupFotoTecho",
        "MantColectores",
    }

    _FOTOVOLTAICO_FIELDS = {
        "InstTerSisFv",
        "SupInstTerSisFv",
        "ImpSisFv",
        "SupImptSisFv",
        "PotIns",
        "MantSfv",
        # si en tu DTO FV también van estos, agrégalos acá:
        # "SupFotoTecho", "FotoTecho", etc. (solo si aplica)
    }

    def _section_dict(self, d: Division, fields: set[str]) -> Dict[str, Any]:
        """
        Construye un dict para los DTOs de detalle.
        Incluye DivisionId y Version para consistencia.
        """
        out: Dict[str, Any] = {
            "DivisionId": getattr(d, "Id", None),
            "Version": getattr(d, "Version", None),
        }
        for f in fields:
            out[f] = getattr(d, f, None)
        return out

    # ---------- Iluminación ----------
    def get_iluminacion(self, db: Session, division_id: int) -> Dict[str, Any]:
        d = self.get(db, division_id)
        return self._section_dict(d, self._ILUMINACION_FIELDS)

    def update_iluminacion(
        self, db: Session, division_id: int, payload: Dict[str, Any], user: Optional[str] = None
    ) -> Dict[str, Any]:
        # update() ya filtra por _SYSTEM_FIELDS, así que es seguro.
        self.update(db, division_id, payload=payload, user=user)
        return self.get_iluminacion(db, division_id)

    # ---------- Calefacción ----------
    def get_calefaccion(self, db: Session, division_id: int) -> Dict[str, Any]:
        d = self.get(db, division_id)
        return self._section_dict(d, self._CALEFACCION_FIELDS)

    def update_calefaccion(
        self, db: Session, division_id: int, payload: Dict[str, Any], user: Optional[str] = None
    ) -> Dict[str, Any]:
        self.update(db, division_id, payload=payload, user=user)
        return self.get_calefaccion(db, division_id)

    # ---------- Refrigeración ----------
    def get_refrigeracion(self, db: Session, division_id: int) -> Dict[str, Any]:
        d = self.get(db, division_id)
        return self._section_dict(d, self._REFRIGERACION_FIELDS)

    def update_refrigeracion(
        self, db: Session, division_id: int, payload: Dict[str, Any], user: Optional[str] = None
    ) -> Dict[str, Any]:
        self.update(db, division_id, payload=payload, user=user)
        return self.get_refrigeracion(db, division_id)

    # ---------- ACS ----------
    def get_acs(self, db: Session, division_id: int) -> Dict[str, Any]:
        d = self.get(db, division_id)
        return self._section_dict(d, self._ACS_FIELDS)

    def update_acs(
        self, db: Session, division_id: int, payload: Dict[str, Any], user: Optional[str] = None
    ) -> Dict[str, Any]:
        self.update(db, division_id, payload=payload, user=user)
        return self.get_acs(db, division_id)

    # ---------- Fotovoltaico ----------
    def get_fotovoltaico(self, db: Session, division_id: int) -> Dict[str, Any]:
        d = self.get(db, division_id)
        return self._section_dict(d, self._FOTOVOLTAICO_FIELDS)

    def update_fotovoltaico(
        self, db: Session, division_id: int, payload: Dict[str, Any], user: Optional[str] = None
    ) -> Dict[str, Any]:
        self.update(db, division_id, payload=payload, user=user)
        return self.get_fotovoltaico(db, division_id)