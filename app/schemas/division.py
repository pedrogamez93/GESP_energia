from __future__ import annotations
from typing import Optional, List, Any
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

# ─────────────────────────────────────────────────────────────────────────────
# Helpers de normalización para Pydantic v2
# ─────────────────────────────────────────────────────────────────────────────
def _to_int_maybe(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    try:
        s = str(v).strip()
        # corta decimales tipo "7.0"
        if "." in s:
            s = s.split(".", 1)[0]
        return int(s)
    except Exception:
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


# ---------- EXISTENTES (ajustados a Pydantic v2) ----------
class DivisionSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class DivisionListDTO(DivisionSelectDTO):
    Active: Optional[bool] = True
    ServicioId: Optional[int] = None
    RegionId: Optional[int] = None
    ComunaId: Optional[int] = None
    DireccionInmuebleId: Optional[int] = None

    # NUEVOS ya expuestos en list()
    IndicadorEE: Optional[int] = None
    AccesoFactura: Optional[int] = None
    ComparteMedidorElectricidad: Optional[bool] = None
    ComparteMedidorGasCanieria: Optional[bool] = None

    # Campos adicionales que ahora también salen en list()
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
    DpSt1: Optional[int] = None
    DpSt2: Optional[int] = None
    DpSt3: Optional[int] = None
    DpSt4: Optional[int] = None
    OrganizacionResponsable: Optional[str] = None
    ServicioResponsableId: Optional[int] = None
    InstitucionResponsableId: Optional[int] = None
    JustificaRol: Optional[str] = None
    SinRol: Optional[bool] = None
    Compromiso2022: Optional[int] = None
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
    MantColectores: Optional[bool] = None
    MantSfv: Optional[bool] = None
    CargaPosteriorT: Optional[bool] = None
    IndicadorEnegia: Optional[float] = None
    ObsInexistenciaEyV: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    # Normalización también para listados
    @model_validator(mode="before")
    @classmethod
    def _normalize_list(cls, data):
        if isinstance(data, dict):
            gv = data.get("GeVersion")
            if gv is not None:
                data["GeVersion"] = _to_int_maybe(gv)

            ind = data.get("IndicadorEnegia")
            if ind is not None:
                data["IndicadorEnegia"] = _to_float_maybe(ind)
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

    # ⬇️ Campo conflictivo (viene a veces como string mezclado):
    Pisos: Optional[int] = None
    # ⬇️ Guardamos el valor original cuando no era parseable:
    PisosTexto: Optional[str] = None

    TipoUsoId: Optional[int] = None
    NroRol: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    # Normaliza y evita ResponseValidationError
    @model_validator(mode="before")
    @classmethod
    def _normalize_detail(cls, data):
        if not isinstance(data, dict):
            return data

        # Pisos: intenta a int; si no se puede, lo deja en PisosTexto y nulifica Pisos
        raw_pisos = data.get("Pisos")
        if raw_pisos is not None and not isinstance(raw_pisos, int):
            parsed = _to_int_maybe(raw_pisos)
            if parsed is None:
                data["PisosTexto"] = str(raw_pisos)
                data["Pisos"] = None
            else:
                data["Pisos"] = parsed
                data.setdefault("PisosTexto", None)

        # Coherencia de otros campos que llegan como string
        gv = data.get("GeVersion")
        if gv is not None:
            data["GeVersion"] = _to_int_maybe(gv)

        ind = data.get("IndicadorEnegia")
        if ind is not None:
            data["IndicadorEnegia"] = _to_float_maybe(ind)

        return data


# ---------- NUEVOS: equivalentes a DTOs .NET ----------
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


# ---------- NUEVO: page para listados ----------
class DivisionPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DivisionListDTO]
    model_config = ConfigDict(from_attributes=True)
