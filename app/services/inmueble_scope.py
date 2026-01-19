# app/services/inmueble_scope.py
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.auth import UserPublic
from app.db.models.division import Division

# pivotes / modelos opcionales (depende tu repo)
try:
    from app.db.models.usuarios_divisiones import UsuarioDivision  # type: ignore
except Exception:
    UsuarioDivision = None  # type: ignore

try:
    from app.db.models.usuarios_servicios import UsuarioServicio  # type: ignore
except Exception:
    UsuarioServicio = None  # type: ignore

try:
    from app.db.models.usuarios_instituciones import UsuarioInstitucion  # type: ignore
except Exception:
    UsuarioInstitucion = None  # type: ignore

try:
    from app.db.models.servicio import Servicio  # type: ignore
except Exception:
    Servicio = None  # type: ignore

try:
    from app.db.models.usuarios_unidades import UsuarioUnidad  # type: ignore
except Exception:
    UsuarioUnidad = None  # type: ignore

try:
    from app.services.unidad_scope import division_id_from_unidad  # type: ignore
except Exception:
    division_id_from_unidad = None  # type: ignore


def is_admin(user: UserPublic) -> bool:
    return "ADMINISTRADOR" in (user.roles or [])


def _get_division_servicio_id(db: Session, division_id: int) -> Optional[int]:
    row = db.execute(
        select(Division.ServicioId).where(Division.Id == int(division_id)).limit(1)
    ).first()
    if not row:
        return None
    return int(row[0]) if row[0] is not None else None


def ensure_actor_can_edit_division(db: Session, actor: UserPublic, division_id: int) -> None:
    """
    Scope robusto para editar un inmueble/división:

    ✅ ADMIN: puede todo

    ✅ Gestor: permitido si cumple al menos una:
      1) UsuarioDivision (vínculo directo a la división)
      2) UsuarioServicio (Division.ServicioId dentro de servicios del actor)
      3) UsuarioInstitucion (institución del Servicio del inmueble está en instituciones del actor)
      4) UsuarioUnidad (si existe): el actor tiene una unidad cuyo inmueble resuelve a division_id

    Si faltan tablas/modelos, NO abrimos permisos: devolvemos 403 (fail-closed).
    """

    if is_admin(actor):
        return

    # ¿Existe la división?
    dv = db.execute(
        select(Division.Id, Division.ServicioId).where(Division.Id == int(division_id)).limit(1)
    ).first()
    if not dv:
        raise HTTPException(status_code=404, detail="Inmueble/División no encontrado")

    dv_servicio_id = int(dv[1]) if dv[1] is not None else None

    # 1) Directo por Division
    if UsuarioDivision is not None:
        ok = db.execute(
            select(UsuarioDivision.DivisionId)
            .where(
                UsuarioDivision.UsuarioId == actor.id,
                UsuarioDivision.DivisionId == int(division_id),
            )
            .limit(1)
        ).first()
        if ok:
            return

    # 2) Por Servicio del inmueble
    if dv_servicio_id is not None and UsuarioServicio is not None:
        ok = db.execute(
            select(UsuarioServicio.ServicioId)
            .where(
                UsuarioServicio.UsuarioId == actor.id,
                UsuarioServicio.ServicioId == int(dv_servicio_id),
            )
            .limit(1)
        ).first()
        if ok:
            return

    # 3) Por Institución del servicio del inmueble
    if dv_servicio_id is not None and UsuarioInstitucion is not None and Servicio is not None:
        ok = db.execute(
            select(Servicio.Id)
            .join(UsuarioInstitucion, UsuarioInstitucion.InstitucionId == Servicio.InstitucionId)
            .where(
                Servicio.Id == int(dv_servicio_id),
                UsuarioInstitucion.UsuarioId == actor.id,
            )
            .limit(1)
        ).first()
        if ok:
            return

    # 4) Por Unidad -> Inmueble (si existe UsuariosUnidades + helper)
    if UsuarioUnidad is not None and division_id_from_unidad is not None:
        rows = db.execute(
            select(UsuarioUnidad.UnidadId).where(UsuarioUnidad.UsuarioId == actor.id)
        ).all()
        for (uid,) in rows:
            if uid is None:
                continue
            try:
                iid = division_id_from_unidad(db, int(uid))
            except Exception:
                continue
            if int(iid) == int(division_id):
                return

    raise HTTPException(
        status_code=403,
        detail={
            "code": "forbidden_scope",
            "msg": "No puedes modificar este inmueble/división (fuera de tu alcance).",
            "division_id": int(division_id),
        },
    )


def ensure_actor_can_touch_unidad(db: Session, actor: UserPublic, unidad_id: int) -> None:
    """
    Seguridad extra: al vincular/desvincular una unidad, valida que el actor
    pueda operar sobre ESA unidad.

    ✅ ADMIN: todo
    ✅ Si existe UsuariosUnidades: exige que la unidad esté asignada al actor.
    Si no existe el modelo, fail-closed (403).
    """
    if is_admin(actor):
        return

    if UsuarioUnidad is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede verificar alcance por unidad (UsuariosUnidades no disponible).",
                "unidad_id": int(unidad_id),
            },
        )

    ok = db.execute(
        select(UsuarioUnidad.UnidadId)
        .where(
            UsuarioUnidad.UsuarioId == actor.id,
            UsuarioUnidad.UnidadId == int(unidad_id),
        )
        .limit(1)
    ).first()

    if not ok:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No puedes operar sobre esa unidad (fuera de tu alcance).",
                "unidad_id": int(unidad_id),
            },
        )


def ensure_actor_can_create_inmueble_for_servicio(db: Session, actor: UserPublic, servicio_id: int) -> None:
    """
    Permite que gestores creen inmuebles SOLO si el ServicioId está en su scope
    (por UsuarioServicio o por UsuarioInstitucion derivado de Servicio.InstitucionId).

    ✅ ADMIN: todo
    """
    if is_admin(actor):
        return

    sid = int(servicio_id)

    allowed = False

    if UsuarioServicio is not None:
        ok = db.execute(
            select(UsuarioServicio.ServicioId)
            .where(
                UsuarioServicio.UsuarioId == actor.id,
                UsuarioServicio.ServicioId == sid,
            )
            .limit(1)
        ).first()
        if ok:
            allowed = True

    if not allowed and UsuarioInstitucion is not None and Servicio is not None:
        ok = db.execute(
            select(Servicio.Id)
            .join(UsuarioInstitucion, UsuarioInstitucion.InstitucionId == Servicio.InstitucionId)
            .where(
                Servicio.Id == sid,
                UsuarioInstitucion.UsuarioId == actor.id,
            )
            .limit(1)
        ).first()
        if ok:
            allowed = True

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No puedes crear inmuebles para un servicio fuera de tu alcance.",
                "ServicioId": sid,
            },
        )
