from __future__ import annotations
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.division import Division
from app.db.models.tipo_equipo_calefaccion_energetico import TipoEquipoCalefaccionEnergetico as Compat
from app.db.models.energetico import Energetico
from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.db.models.tipo_luminaria import TipoLuminaria
from app.db.models.tipo_colector import TipoColector


class DivisionSistemasService:

    # ---------- helpers ----------
    @staticmethod
    def _exists_fk(db: Session, model, id_: int | None, label: str):
        if id_ is None:
            return
        if db.get(model, id_) is None:
            raise HTTPException(status_code=400, detail=f"{label} {id_} no existe")

    @staticmethod
    def _is_compatible(db: Session, equipo_id: int | None, energetico_id: int | None) -> bool:
        if not equipo_id or not energetico_id:
            return True
        q = (
            db.query(Compat)
            .filter(
                Compat.TipoEquipoCalefaccionId == equipo_id,
                Compat.EnergeticoId == energetico_id,
            )
            .first()
        )
        return q is not None

    # ---------- read ----------
    def get(self, db: Session, division_id: int) -> Division:
        div = db.get(Division, division_id)
        if not div:
            raise HTTPException(status_code=404, detail="División no encontrada")
        return div

    def to_dto(self, div: Division) -> dict:
        return dict(
            DivisionId=div.Id,

            TipoLuminariaId=div.TipoLuminariaId,

            EquipoCalefaccionId=div.EquipoCalefaccionId,
            EnergeticoCalefaccionId=div.EnergeticoCalefaccionId,
            TempSeteoCalefaccionId=div.TempSeteoCalefaccionId,

            EquipoRefrigeracionId=div.EquipoRefrigeracionId,
            EnergeticoRefrigeracionId=div.EnergeticoRefrigeracionId,
            TempSeteoRefrigeracionId=div.TempSeteoRefrigeracionId,

            EquipoAcsId=div.EquipoAcsId,
            EnergeticoAcsId=div.EnergeticoAcsId,
            SistemaSolarTermico=div.SistemaSolarTermico,
            ColectorId=div.ColectorId,
            SupColectores=div.SupColectores,
            FotoTecho=div.FotoTecho,
            SupFotoTecho=div.SupFotoTecho,
            InstTerSisFv=div.InstTerSisFv,
            SupInstTerSisFv=div.SupInstTerSisFv,
            ImpSisFv=div.ImpSisFv,
            SupImptSisFv=div.SupImptSisFv,
            PotIns=div.PotIns,
            MantColectores=div.MantColectores,
            MantSfv=div.MantSfv,

            Version=div.Version,
        )

    # ---------- update ----------
    def update(self, db: Session, division_id: int, data: dict, user: str | None = None) -> Division:
        div = self.get(db, division_id)

        # Validar FKs si vienen en el payload (existencia en catálogos)
        self._exists_fk(db, TipoLuminaria, data.get("TipoLuminariaId"), "TipoLuminaria")
        self._exists_fk(db, TipoEquipoCalefaccion, data.get("EquipoCalefaccionId"), "TipoEquipoCalefaccion")
        self._exists_fk(db, TipoEquipoCalefaccion, data.get("EquipoRefrigeracionId"), "TipoEquipoCalefaccion")
        self._exists_fk(db, TipoEquipoCalefaccion, data.get("EquipoAcsId"), "TipoEquipoCalefaccion")
        self._exists_fk(db, Energetico, data.get("EnergeticoCalefaccionId"), "Energetico")
        self._exists_fk(db, Energetico, data.get("EnergeticoRefrigeracionId"), "Energetico")
        self._exists_fk(db, Energetico, data.get("EnergeticoAcsId"), "Energetico")
        self._exists_fk(db, TipoColector, data.get("ColectorId"), "TipoColector")

        # Armar “valores finales” (lo nuevo si viene, si no el actual)
        final = {
            "EquipoCalefaccionId": data.get("EquipoCalefaccionId", div.EquipoCalefaccionId),
            "EnergeticoCalefaccionId": data.get("EnergeticoCalefaccionId", div.EnergeticoCalefaccionId),
            "EquipoRefrigeracionId": data.get("EquipoRefrigeracionId", div.EquipoRefrigeracionId),
            "EnergeticoRefrigeracionId": data.get("EnergeticoRefrigeracionId", div.EnergeticoRefrigeracionId),
            "EquipoAcsId": data.get("EquipoAcsId", div.EquipoAcsId),
            "EnergeticoAcsId": data.get("EnergeticoAcsId", div.EnergeticoAcsId),
            "SistemaSolarTermico": data.get("SistemaSolarTermico", div.SistemaSolarTermico),
            "ColectorId": data.get("ColectorId", div.ColectorId),
            "SupColectores": data.get("SupColectores", div.SupColectores),
        }

        # Compatibilidades equipo↔energético (3 pares)
        checks = [
            ("EquipoCalefaccionId", "EnergeticoCalefaccionId", "calefacción"),
            ("EquipoRefrigeracionId", "EnergeticoRefrigeracionId", "refrigeración"),
            ("EquipoAcsId", "EnergeticoAcsId", "ACS"),
        ]
        for ek, en, etiqueta in checks:
            if (final.get(ek) or final.get(en)) and not self._is_compatible(db, final.get(ek), final.get(en)):
                raise HTTPException(status_code=400, detail=f"Energético no compatible con el equipo en {etiqueta}")

        # Reglas ACS: si hay solar térmico, exigir colector y superficie > 0
        if final["SistemaSolarTermico"]:
            if not final["ColectorId"] or (final["SupColectores"] or 0) <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Si 'SistemaSolarTermico' es true, 'ColectorId' y 'SupColectores' (> 0) son obligatorios."
                )

        # Aplicar cambios
        for k, v in data.items():
            setattr(div, k, v)

        # Auditoría mínima (según tu modelo)
        div.UpdatedAt = datetime.utcnow()
        div.Version = (div.Version or 0) + 1
        if user:
            div.ModifiedBy = user

        db.add(div)
        db.commit()
        db.refresh(div)
        return div

    # ---------- catálogos (select liviano) ----------
    def catalogs(self, db: Session):
        # Retorna mínimos para combos: Id, Nombre
        # Nota: tu modelo TipoEquipoCalefaccion no expone AC/CA/FR; devolvemos todo.
        from sqlalchemy import select

        def _rows(stmt):
            return [{"Id": r[0], "Nombre": r[1]} for r in db.execute(stmt).all()]

        from app.db.models.tipo_luminaria import TipoLuminaria
        from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
        from app.db.models.energetico import Energetico
        from app.db.models.tipo_colector import TipoColector
        from app.db.models.tipo_equipo_calefaccion_energetico import TipoEquipoCalefaccionEnergetico

        luminarias = _rows(select(TipoLuminaria.Id, TipoLuminaria.Nombre).order_by(TipoLuminaria.Nombre))
        equipos = _rows(select(TipoEquipoCalefaccion.Id, TipoEquipoCalefaccion.Nombre).order_by(TipoEquipoCalefaccion.Nombre))
        energeticos = _rows(select(Energetico.Id, Energetico.Nombre).order_by(Energetico.Nombre))
        colectores = _rows(select(TipoColector.Id, TipoColector.Nombre).order_by(TipoColector.Nombre))

        # Energeticos permitidos por equipo
        rel = db.query(TipoEquipoCalefaccionEnergetico).all()
        por_equipo: dict[int, list[int]] = {}
        for r in rel:
            por_equipo.setdefault(r.TipoEquipoCalefaccionId, []).append(r.EnergeticoId)

        return dict(
            Luminarias=luminarias,
            Equipos=equipos,
            Energeticos=energeticos,
            TiposColectores=colectores,
            EnergeticosPorEquipo=por_equipo,  # {equipoId: [energeticoId, ...]}
        )
