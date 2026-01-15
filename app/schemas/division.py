from __future__ import annotations

from typing import Optional, List, Any
from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, model_validator

# ─────────────────────────────────────────────────────────────────────────────
# Helpers de normalización para Pydantic v2
# ─────────────────────────────────────────────────────────────────────────────
_INT_RE = re.compile(r"^\s*-?\d+\s*$")


def _to_int_maybe(v: Any) -> Optional[int]:
    """
    Convierte a int si:
    - Es int ya
    - Es bool (True->1, False->0)
    - Es string con solo dígitos (y signo), p.ej. '7', '-1'
    - Es string flotante exacta entera '7.0' / '15.00' (sin resto)
    Si no, retorna None (ej: '-1,1,Entrepiso,7,8' → None).
    """
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v

    s = str(v).strip()

    # entero puro
    if _INT_RE.match(s):
        try:
            return int(s)
        except Exception:
            return None

    # flotante que representa entero exacto (7.0 → 7)
    try:
        f = float(s.replace(",", "."))
        if f.is_integer():
            return int(f)
    except Exception:
        pass

    return None


def _to_float_maybe(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        s = str(v).strip().replace(",", ".")
        return float(s)
    except Exception:
        return None


def _blank_to_none(v: Any) -> Any:
    return None if isinstance(v, str) and v.strip() == "" else v


def _to_bool_maybe(v: Any) -> Optional[bool]:
    """
    Normaliza bools que vienen como 0/1, "0"/"1", "true"/"false", etc.
    """
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    iv = _to_int_maybe(v)
    if iv is not None:
        return bool(iv)
    s = str(v).strip().lower()
    if s in ("true", "t", "yes", "y", "si", "sí"):
        return True
    if s in ("false", "f", "no", "n"):
        return False
    return None


# ─────────────────────────────────────────────────────────────────────────────
# DTOs
# ─────────────────────────────────────────────────────────────────────────────

class DivisionSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class DivisionListDTO(DivisionSelectDTO):
    """
    DTO liviano para listados.

    NOTA:
    - Tipos alineados al modelo SQLAlchemy:
      * IndicadorEE: bool
      * DpSt1..DpSt4: bool
      * Compromiso2022: bool|None
    """
    Active: Optional[bool] = True
    ServicioId: Optional[int] = None
    RegionId: Optional[int] = None
    ComunaId: Optional[int] = None
    DireccionInmuebleId: Optional[int] = None

    Funcionarios: Optional[int] = None

    IndicadorEE: Optional[bool] = None
    AccesoFactura: Optional[int] = None
    ComparteMedidorElectricidad: Optional[bool] = None
    ComparteMedidorGasCanieria: Optional[bool] = None

    ProvinciaId: Optional[int] = None
    Direccion: Optional[str] = None

    PisosIguales: Optional[bool] = None
    NivelPaso3: Optional[int] = None

    Calle: Optional[str] = None
    Numero: Optional[str] = None

    GeVersion: Optional[int] = None
    ParentId: Optional[int] = None

    TipoAdministracionId: Optional[int] = None
    TipoInmueble: Optional[int] = None
    AdministracionServicioId: Optional[int] = None

    DpSt1: Optional[bool] = None
    DpSt2: Optional[bool] = None
    DpSt3: Optional[bool] = None
    DpSt4: Optional[bool] = None

    OrganizacionResponsable: Optional[str] = None
    ServicioResponsableId: Optional[int] = None
    InstitucionResponsableId: Optional[int] = None

    JustificaRol: Optional[str] = None
    SinRol: Optional[bool] = None

    Compromiso2022: Optional[bool] = None
    Justificacion: Optional[str] = None
    ObservacionCompromiso2022: Optional[str] = None
    EstadoCompromiso2022: Optional[int] = None

    AnioInicioGestionEnergetica: Optional[int] = None
    AnioInicioRestoItems: Optional[int] = None

    DisponeVehiculo: Optional[bool] = None
    VehiculosIds: Optional[str] = None

    AireAcondicionadoElectricidad: Optional[bool] = None
    CalefaccionGas: Optional[bool] = None
    DisponeCalefaccion: Optional[bool] = None

    NroOtrosColaboradores: Optional[int] = None

    ObservacionPapel: Optional[str] = None
    ObservaPapel: Optional[bool] = None

    ObservacionResiduos: Optional[str] = None
    ObservaResiduos: Optional[bool] = None

    ObservacionAgua: Optional[str] = None
    ObservaAgua: Optional[bool] = None

    JustificaResiduos: Optional[bool] = None
    JustificacionResiduos: Optional[str] = None

    ReportaEV: Optional[bool] = None
    TieneMedidorElectricidad: Optional[bool] = None
    TieneMedidorGas: Optional[bool] = None

    AccesoFacturaAgua: Optional[int] = None
    InstitucionResponsableAguaId: Optional[int] = None
    OrganizacionResponsableAgua: Optional[str] = None
    ServicioResponsableAguaId: Optional[int] = None
    ComparteMedidorAgua: Optional[bool] = None

    NoDeclaraImpresora: Optional[bool] = None
    NoDeclaraArtefactos: Optional[bool] = None
    NoDeclaraContenedores: Optional[bool] = None
    GestionBienes: Optional[bool] = None

    UsaBidon: Optional[bool] = None
    JustificaResiduosNoReciclados: Optional[bool] = None
    JustificacionResiduosNoReciclados: Optional[str] = None

    ColectorId: Optional[int] = None
    EnergeticoAcsId: Optional[int] = None
    EnergeticoCalefaccionId: Optional[int] = None
    EnergeticoRefrigeracionId: Optional[int] = None
    EquipoAcsId: Optional[int] = None
    EquipoCalefaccionId: Optional[int] = None
    EquipoRefrigeracionId: Optional[int] = None

    FotoTecho: Optional[bool] = None
    ImpSisFv: Optional[bool] = None
    InstTerSisFv: Optional[bool] = None
    PotIns: Optional[float] = None
    SistemaSolarTermico: Optional[bool] = None

    SupColectores: Optional[float] = None
    SupFotoTecho: Optional[float] = None
    SupImptSisFv: Optional[float] = None
    SupInstTerSisFv: Optional[float] = None

    TempSeteoCalefaccionId: Optional[int] = None
    TempSeteoRefrigeracionId: Optional[int] = None
    TipoLuminariaId: Optional[int] = None

    MantColectores: Optional[int] = None
    MantSfv: Optional[int] = None

    CargaPosteriorT: Optional[bool] = None
    IndicadorEnegia: Optional[float] = None
    ObsInexistenciaEyV: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _normalize_list(cls, data):
        if isinstance(data, dict):
            data["GeVersion"] = _to_int_maybe(data.get("GeVersion"))
            data["IndicadorEnegia"] = _to_float_maybe(data.get("IndicadorEnegia"))

            # booleans típicos
            for bk in (
                "DpSt1", "DpSt2", "DpSt3", "DpSt4",
                "Compromiso2022",
                "IndicadorEE",
            ):
                if bk in data:
                    data[bk] = _to_bool_maybe(data.get(bk))

            for bk in (
                "ComparteMedidorElectricidad",
                "ComparteMedidorGasCanieria",
                "PisosIguales",
                "SinRol",
                "DisponeVehiculo",
                "AireAcondicionadoElectricidad",
                "CalefaccionGas",
                "DisponeCalefaccion",
                "ObservaPapel",
                "ObservaResiduos",
                "ObservaAgua",
                "JustificaResiduos",
                "ReportaEV",
                "TieneMedidorElectricidad",
                "TieneMedidorGas",
                "ComparteMedidorAgua",
                "NoDeclaraImpresora",
                "NoDeclaraArtefactos",
                "NoDeclaraContenedores",
                "GestionBienes",
                "UsaBidon",
                "JustificaResiduosNoReciclados",
                "FotoTecho",
                "ImpSisFv",
                "InstTerSisFv",
                "SistemaSolarTermico",
                "CargaPosteriorT",
            ):
                if bk in data:
                    data[bk] = _to_bool_maybe(data.get(bk))

            # ints típicos
            for ik in (
                "Funcionarios",
                "AccesoFactura",
                "NivelPaso3",
                "AccesoFacturaAgua",
                "ProvinciaId",
                "RegionId",
                "ComunaId",
                "DireccionInmuebleId",
                "ServicioId",
                "ParentId",
                "TipoAdministracionId",
                "TipoInmueble",
                "AdministracionServicioId",
                "ServicioResponsableId",
                "InstitucionResponsableId",
                "EstadoCompromiso2022",
                "AnioInicioGestionEnergetica",
                "AnioInicioRestoItems",
                "NroOtrosColaboradores",
                "InstitucionResponsableAguaId",
                "ServicioResponsableAguaId",
                "ColectorId",
                "EnergeticoAcsId",
                "EnergeticoCalefaccionId",
                "EnergeticoRefrigeracionId",
                "EquipoAcsId",
                "EquipoCalefaccionId",
                "EquipoRefrigeracionId",
                "TempSeteoCalefaccionId",
                "TempSeteoRefrigeracionId",
                "TipoLuminariaId",
                "MantColectores",
                "MantSfv",
            ):
                if ik in data:
                    data[ik] = _to_int_maybe(data.get(ik))

            # floats típicos
            for fk in (
                "PotIns",
                "SupColectores",
                "SupFotoTecho",
                "SupImptSisFv",
                "SupInstTerSisFv",
                "IndicadorEnegia",
            ):
                if fk in data:
                    data[fk] = _to_float_maybe(data.get(fk))

            # limpiar strings vacíos frecuentes
            for k in ("Direccion", "Calle", "Numero", "OrganizacionResponsable"):
                if k in data:
                    data[k] = _blank_to_none(data.get(k))
        return data


class DivisionDTO(DivisionListDTO):
    CreatedAt: Optional[datetime] = None
    UpdatedAt: Optional[datetime] = None
    Version: Optional[int] = None

    EdificioId: Optional[int] = None
    ReportaPMG: Optional[bool] = None
    AnyoConstruccion: Optional[int] = None

    Latitud: Optional[float] = None
    Longitud: Optional[float] = None

    TipoUnidadId: Optional[int] = None
    TipoPropiedadId: Optional[int] = None
    Superficie: Optional[float] = None

    # conflictivo
    Pisos: Optional[int] = None
    PisosTexto: Optional[str] = None

    TipoUsoId: Optional[int] = None
    NroRol: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _normalize_detail(cls, data):
        if not isinstance(data, dict):
            return data

        raw_pisos = data.get("Pisos")
        if raw_pisos is not None and not isinstance(raw_pisos, int):
            parsed = _to_int_maybe(raw_pisos)
            if parsed is None:
                data["PisosTexto"] = str(raw_pisos)
                data["Pisos"] = None
            else:
                data["Pisos"] = parsed
                data.setdefault("PisosTexto", None)

        data["GeVersion"] = _to_int_maybe(data.get("GeVersion"))
        data["IndicadorEnegia"] = _to_float_maybe(data.get("IndicadorEnegia"))

        data["AnyoConstruccion"] = _to_int_maybe(data.get("AnyoConstruccion"))
        data["Latitud"] = _to_float_maybe(data.get("Latitud"))
        data["Longitud"] = _to_float_maybe(data.get("Longitud"))

        data["NroRol"] = _blank_to_none(data.get("NroRol"))

        # booleans típicos
        for bk in (
            "DpSt1", "DpSt2", "DpSt3", "DpSt4",
            "Compromiso2022",
            "IndicadorEE",
            "ReportaPMG",
        ):
            if bk in data:
                data[bk] = _to_bool_maybe(data.get(bk))

        return data


# ─────────────────────────────────────────────────────────────────────────────
# ✅ NUEVO: DTO para CREATE (POST) - en el MISMO ARCHIVO
# ─────────────────────────────────────────────────────────────────────────────
class DivisionCreate(BaseModel):
    """
    DTO para crear Divisiones.
    - No incluye Id (lo genera la BD)
    - No incluye CreatedAt/UpdatedAt/Version (los maneja el service)
    - Permite enviar todos los campos del modelo.
    """

    # estado / tracking
    Active: Optional[bool] = True
    ModifiedBy: Optional[str] = None
    CreatedBy: Optional[str] = None

    # base
    Funcionarios: Optional[int] = 0
    Nombre: Optional[str] = None
    ReportaPMG: Optional[bool] = False
    AnyoConstruccion: Optional[int] = None

    Latitud: Optional[float] = None
    Longitud: Optional[float] = None

    # fks principales (en tu modelo son NOT NULL, pero igual permitimos None y el service decide)
    EdificioId: Optional[int] = None
    ServicioId: Optional[int] = None
    TipoPropiedadId: Optional[int] = None

    # resto de campos
    TipoUnidadId: Optional[int] = None
    Superficie: Optional[float] = None
    Pisos: Optional[int] = None
    PisosTexto: Optional[str] = None
    TipoUsoId: Optional[int] = None
    NroRol: Optional[str] = None
    Direccion: Optional[str] = None

    ComparteMedidorElectricidad: Optional[bool] = False
    ComparteMedidorGasCanieria: Optional[bool] = False
    PisosIguales: Optional[bool] = True
    NivelPaso3: Optional[int] = 0

    Calle: Optional[str] = None
    ComunaId: Optional[int] = None
    Numero: Optional[str] = None

    GeVersion: Optional[int] = 0
    ParentId: Optional[int] = None
    ProvinciaId: Optional[int] = None
    RegionId: Optional[int] = None
    TipoAdministracionId: Optional[int] = None
    TipoInmueble: Optional[int] = None
    AdministracionServicioId: Optional[int] = None

    DpSt1: Optional[bool] = False
    DpSt2: Optional[bool] = False
    DpSt3: Optional[bool] = False
    DpSt4: Optional[bool] = False

    DireccionInmuebleId: Optional[int] = None
    AccesoFactura: Optional[int] = 0
    OrganizacionResponsable: Optional[str] = None
    ServicioResponsableId: Optional[int] = None
    InstitucionResponsableId: Optional[int] = None
    IndicadorEE: Optional[bool] = False
    JustificaRol: Optional[str] = None
    SinRol: Optional[bool] = False

    Compromiso2022: Optional[bool] = None
    Justificacion: Optional[str] = None
    ObservacionCompromiso2022: Optional[str] = None
    EstadoCompromiso2022: Optional[int] = None
    AnioInicioGestionEnergetica: Optional[int] = None
    AnioInicioRestoItems: Optional[int] = None

    DisponeVehiculo: Optional[bool] = None
    VehiculosIds: Optional[str] = None

    AireAcondicionadoElectricidad: Optional[bool] = False
    CalefaccionGas: Optional[bool] = False
    DisponeCalefaccion: Optional[bool] = False

    NroOtrosColaboradores: Optional[int] = 0
    ObservacionPapel: Optional[str] = None
    ObservaPapel: Optional[bool] = False
    ObservacionResiduos: Optional[str] = None
    ObservaResiduos: Optional[bool] = False
    ObservacionAgua: Optional[str] = None
    ObservaAgua: Optional[bool] = False
    JustificaResiduos: Optional[bool] = False
    JustificacionResiduos: Optional[str] = None

    ReportaEV: Optional[bool] = False
    TieneMedidorElectricidad: Optional[bool] = False
    TieneMedidorGas: Optional[bool] = False
    AccesoFacturaAgua: Optional[int] = None
    InstitucionResponsableAguaId: Optional[int] = None
    OrganizacionResponsableAgua: Optional[str] = None
    ServicioResponsableAguaId: Optional[int] = None
    ComparteMedidorAgua: Optional[bool] = False

    NoDeclaraImpresora: Optional[bool] = None
    NoDeclaraArtefactos: Optional[bool] = None
    NoDeclaraContenedores: Optional[bool] = None
    GestionBienes: Optional[bool] = None

    UsaBidon: Optional[bool] = False
    JustificaResiduosNoReciclados: Optional[bool] = False
    JustificacionResiduosNoReciclados: Optional[str] = None

    ColectorId: Optional[int] = None
    EnergeticoAcsId: Optional[int] = None
    EnergeticoCalefaccionId: Optional[int] = None
    EnergeticoRefrigeracionId: Optional[int] = None
    EquipoAcsId: Optional[int] = None
    EquipoCalefaccionId: Optional[int] = None
    EquipoRefrigeracionId: Optional[int] = None

    FotoTecho: Optional[bool] = False
    ImpSisFv: Optional[bool] = False
    InstTerSisFv: Optional[bool] = False
    PotIns: Optional[float] = None
    SistemaSolarTermico: Optional[bool] = False

    SupColectores: Optional[float] = None
    SupFotoTecho: Optional[float] = None
    SupImptSisFv: Optional[float] = None
    SupInstTerSisFv: Optional[float] = None

    TempSeteoCalefaccionId: Optional[int] = None
    TempSeteoRefrigeracionId: Optional[int] = None
    TipoLuminariaId: Optional[int] = None
    MantColectores: Optional[int] = None
    MantSfv: Optional[int] = None

    CargaPosteriorT: Optional[bool] = False
    IndicadorEnegia: Optional[float] = None
    ObsInexistenciaEyV: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _normalize_create(cls, data):
        if not isinstance(data, dict):
            return data

        # Pisos: si viene basura, lo guardamos en PisosTexto
        raw_pisos = data.get("Pisos")
        if raw_pisos is not None and not isinstance(raw_pisos, int):
            parsed = _to_int_maybe(raw_pisos)
            if parsed is None:
                data["PisosTexto"] = str(raw_pisos)
                data["Pisos"] = None
            else:
                data["Pisos"] = parsed

        # ints comunes
        for ik in (
            "Funcionarios", "EdificioId", "ServicioId", "TipoPropiedadId",
            "TipoUnidadId", "TipoUsoId", "ComunaId", "ProvinciaId", "RegionId",
            "GeVersion", "ParentId", "TipoAdministracionId", "TipoInmueble",
            "AdministracionServicioId", "DireccionInmuebleId",
            "AccesoFactura", "ServicioResponsableId", "InstitucionResponsableId",
            "EstadoCompromiso2022", "AnioInicioGestionEnergetica", "AnioInicioRestoItems",
            "NroOtrosColaboradores", "AccesoFacturaAgua",
            "InstitucionResponsableAguaId", "ServicioResponsableAguaId",
            "ColectorId", "EnergeticoAcsId", "EnergeticoCalefaccionId", "EnergeticoRefrigeracionId",
            "EquipoAcsId", "EquipoCalefaccionId", "EquipoRefrigeracionId",
            "TempSeteoCalefaccionId", "TempSeteoRefrigeracionId", "TipoLuminariaId",
            "MantColectores", "MantSfv",
            "AnyoConstruccion",
        ):
            if ik in data:
                data[ik] = _to_int_maybe(data.get(ik))

        # floats
        for fk in ("Latitud", "Longitud", "Superficie", "PotIns", "SupColectores", "SupFotoTecho", "SupImptSisFv", "SupInstTerSisFv", "IndicadorEnegia"):
            if fk in data:
                data[fk] = _to_float_maybe(data.get(fk))

        # bools
        for bk in (
            "Active", "ReportaPMG",
            "ComparteMedidorElectricidad", "ComparteMedidorGasCanieria",
            "PisosIguales", "IndicadorEE", "SinRol",
            "DpSt1", "DpSt2", "DpSt3", "DpSt4",
            "Compromiso2022",
            "DisponeVehiculo",
            "AireAcondicionadoElectricidad", "CalefaccionGas", "DisponeCalefaccion",
            "ObservaPapel", "ObservaResiduos", "ObservaAgua",
            "JustificaResiduos",
            "ReportaEV", "TieneMedidorElectricidad", "TieneMedidorGas",
            "ComparteMedidorAgua",
            "NoDeclaraImpresora", "NoDeclaraArtefactos", "NoDeclaraContenedores",
            "GestionBienes",
            "UsaBidon", "JustificaResiduosNoReciclados",
            "FotoTecho", "ImpSisFv", "InstTerSisFv", "SistemaSolarTermico",
            "CargaPosteriorT",
        ):
            if bk in data:
                data[bk] = _to_bool_maybe(data.get(bk))

        # limpiar strings vacíos
        for sk in (
            "Nombre", "ModifiedBy", "CreatedBy",
            "NroRol", "Direccion", "Calle", "Numero",
            "OrganizacionResponsable", "JustificaRol",
            "Justificacion", "ObservacionCompromiso2022",
            "VehiculosIds",
            "ObservacionPapel", "ObservacionResiduos", "ObservacionAgua",
            "JustificacionResiduos", "JustificacionResiduosNoReciclados",
            "OrganizacionResponsableAgua",
            "ObsInexistenciaEyV",
        ):
            if sk in data:
                data[sk] = _blank_to_none(data.get(sk))

        return data


# ─────────────────────────────────────────────────────────────────────────────
# Nuevos equivalentes a DTOs .NET
# ─────────────────────────────────────────────────────────────────────────────

class ObservacionDTO(BaseModel):
    CheckObserva: bool
    Observacion: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ReportaResiduosDTO(BaseModel):
    CheckReporta: bool
    Justificacion: Optional[str] = None
    CheckReportaNoReciclados: bool = False
    JustificacionNoReciclados: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ObservacionInexistenciaDTO(BaseModel):
    Observacion: str
    model_config = ConfigDict(from_attributes=True)


class DivisionPatchDTO(BaseModel):
    NroRol: Optional[str] = None
    SinRol: bool = False
    JustificaRol: Optional[str] = None

    Funcionarios: int = 0
    NroOtrosColaboradores: int = 0

    DisponeVehiculo: Optional[bool] = None
    VehiculosIds: Optional[str] = None

    AccesoFacturaAgua: Optional[int] = None
    InstitucionResponsableAguaId: Optional[int] = None
    ServicioResponsableAguaId: Optional[int] = None
    OrganizacionResponsableAgua: Optional[str] = None
    ComparteMedidorAgua: Optional[bool] = None

    DisponeCalefaccion: bool = False
    AireAcondicionadoElectricidad: bool = False
    CalefaccionGas: bool = False

    GestionBienes: Optional[bool] = None
    UsaBidon: bool = False

    model_config = ConfigDict(from_attributes=True)


class DivisionAniosDTO(BaseModel):
    Id: int
    AnioInicioGestionEnergetica: Optional[int] = None
    AnioInicioRestoItems: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class OkMessage(BaseModel):
    Ok: bool = True
    Message: str = "ok"
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────────────────────────────────────

class DivisionPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DivisionListDTO]
    model_config = ConfigDict(from_attributes=True)


class DivisionBusquedaEspecificaDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    Direccion: Optional[str] = None
    RegionId: Optional[int] = None
    ServicioId: int

    DireccionInmuebleId: Optional[int] = None
    DireccionComunaId: Optional[int] = None
    EdificioComunaId: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class DivisionBusquedaEspecificaPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DivisionBusquedaEspecificaDTO]
    model_config = ConfigDict(from_attributes=True)
