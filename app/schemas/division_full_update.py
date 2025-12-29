from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DivisionFullUpdate(BaseModel):
    # Identidad / estado
    Active: Optional[bool] = None
    ModifiedBy: Optional[str] = None

    # Datos base
    Funcionarios: Optional[int] = None
    Nombre: Optional[str] = None
    ReportaPMG: Optional[bool] = None
    AnyoConstruccion: Optional[int] = None
    Latitud: Optional[float] = None
    Longitud: Optional[float] = None

    # Relaciones
    EdificioId: Optional[int] = None
    ServicioId: Optional[int] = None
    TipoUnidadId: Optional[int] = None
    TipoPropiedadId: Optional[int] = None
    TipoUsoId: Optional[int] = None

    # Inmueble
    Superficie: Optional[float] = None
    Pisos: Optional[int] = None
    NroRol: Optional[str] = None
    Direccion: Optional[str] = None
    Calle: Optional[str] = None
    Numero: Optional[str] = None
    DireccionInmuebleId: Optional[int] = None

    # Territorial
    ComunaId: Optional[int] = None
    ProvinciaId: Optional[int] = None
    RegionId: Optional[int] = None
    ParentId: Optional[int] = None

    # Indicadores / flags generales
    IndicadorEE: Optional[bool] = None
    IndicadorEnegia: Optional[float] = None   # ✅ FIX: en BD es numérico (38.62 etc.)
    NivelPaso3: Optional[int] = None          # ✅ FIX: en payload viene 0/1
    PisosIguales: Optional[bool] = None

    # Rol / gestión
    JustificaRol: Optional[str] = None
    SinRol: Optional[bool] = None
    Compromiso2022: Optional[bool] = None
    Justificacion: Optional[str] = None
    ObservacionCompromiso2022: Optional[str] = None
    EstadoCompromiso2022: Optional[int] = None
    AnioInicioGestionEnergetica: Optional[int] = None
    AnioInicioRestoItems: Optional[int] = None

    # Vehículos
    DisponeVehiculo: Optional[bool] = None
    VehiculosIds: Optional[str] = None

    # Colaboradores
    NroOtrosColaboradores: Optional[int] = None

    # Agua
    AccesoFacturaAgua: Optional[int] = None
    ComparteMedidorAgua: Optional[bool] = None
    InstitucionResponsableAguaId: Optional[int] = None
    OrganizacionResponsableAgua: Optional[str] = None
    ServicioResponsableAguaId: Optional[int] = None
    UsaBidon: Optional[bool] = None

    # Energía / climatización
    AireAcondicionadoElectricidad: Optional[bool] = None
    CalefaccionGas: Optional[bool] = None
    DisponeCalefaccion: Optional[bool] = None

    # Sistemas
    TipoLuminariaId: Optional[int] = None
    EquipoAcsId: Optional[int] = None
    EquipoCalefaccionId: Optional[int] = None
    EquipoRefrigeracionId: Optional[int] = None
    EnergeticoAcsId: Optional[int] = None
    EnergeticoCalefaccionId: Optional[int] = None
    EnergeticoRefrigeracionId: Optional[int] = None
    TempSeteoCalefaccionId: Optional[int] = None
    TempSeteoRefrigeracionId: Optional[int] = None

    # Solar / FV
    SistemaSolarTermico: Optional[bool] = None
    ColectorId: Optional[int] = None
    SupColectores: Optional[float] = None
    FotoTecho: Optional[bool] = None
    SupFotoTecho: Optional[float] = None

    InstTerSisFv: Optional[bool] = None
    SupInstTerSisFv: Optional[float] = None
    ImpSisFv: Optional[bool] = None
    SupImptSisFv: Optional[float] = None
    PotIns: Optional[float] = None

    MantColectores: Optional[bool] = None
    MantSfv: Optional[bool] = None

    # Medidores
    TieneMedidorElectricidad: Optional[bool] = None
    TieneMedidorGas: Optional[bool] = None
    ComparteMedidorElectricidad: Optional[bool] = None
    ComparteMedidorGasCanieria: Optional[bool] = None

    # Residuos / papel
    ObservaPapel: Optional[bool] = None
    ObservacionPapel: Optional[str] = None
    ObservaResiduos: Optional[bool] = None
    ObservacionResiduos: Optional[str] = None
    ObservaAgua: Optional[bool] = None
    ObservacionAgua: Optional[str] = None
    JustificaResiduos: Optional[bool] = None
    JustificacionResiduos: Optional[str] = None
    JustificaResiduosNoReciclados: Optional[bool] = None
    JustificacionResiduosNoReciclados: Optional[str] = None

    # Otros
    GestionBienes: Optional[bool] = None
    NoDeclaraImpresora: Optional[bool] = None
    NoDeclaraArtefactos: Optional[bool] = None
    NoDeclaraContenedores: Optional[bool] = None
    ReportaEV: Optional[bool] = None
    CargaPosteriorT: Optional[bool] = None
    ObsInexistenciaEyV: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
