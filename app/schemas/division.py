from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator

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
    GeVersion: Optional[int] = None          # llega como entero
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
    IndicadorEnegia: Optional[float] = None  # llega con decimal
    ObsInexistenciaEyV: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


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

    # —— PUNTO CLAVE: normalizamos Pisos y exponemos PisosTexto cuando no es número
    Pisos: Optional[int] = None
    PisosTexto: Optional[str] = None

    TipoUsoId: Optional[int] = None
    NroRol: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    # ---------- Normalizadores tolerantes (evitan 500 por ResponseValidationError) ----------
    @model_validator(mode="before")
    @classmethod
    def _normalize_fields(cls, data):
        """
        - Si 'Pisos' es string mixto (e.g. '-1,1,Entrepiso,7,8'), lo mueve a PisosTexto y deja Pisos=None.
        - Convierte a int seguro: DireccionInmuebleId, IndicadorEE (si llegan como str).
        """
        if not isinstance(data, dict):
            return data

        # Pisos -> entero o PisosTexto
        raw = data.get("Pisos", None)
        if raw is not None:
            if isinstance(raw, int):
                pass  # ok
            elif isinstance(raw, float) and raw.is_integer():
                data["Pisos"] = int(raw)
            else:
                s = str(raw).strip()
                if s.lstrip("+-").isdigit():  # numérico puro (con signo)
                    data["Pisos"] = int(s)
                else:
                    data["PisosTexto"] = s
                    data["Pisos"] = None

        # casteos seguros a int para campos problemáticos
        for key in ("DireccionInmuebleId", "IndicadorEE"):
            v = data.get(key, None)
            if v is None or isinstance(v, int):
                continue
            try:
                s = str(v).strip()
                if s == "" or s.lower() == "null":
                    data[key] = None
                elif s.lstrip("+-").isdigit():
                    data[key] = int(s)
                else:
                    data[key] = None
            except Exception:
                data[key] = None

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
