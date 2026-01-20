from __future__ import annotations
from typing import List, Optional, Union, Any
from pydantic import BaseModel, ConfigDict, Field

# Importa de forma normal; no hay ciclo porque inmuebles.py no importa unidad.py
from app.schemas.inmuebles import InmuebleDTO


# --------- DTOs auxiliares que usa el servicio ---------

class InmuebleTopDTO(BaseModel):
    """Proyección mínima para mostrar Inmuebles asociados a una Unidad."""
    model_config = ConfigDict(from_attributes=True)

    Id: int
    TipoInmueble: Optional[int] = None


class pisoDTO(BaseModel):
    """Proyección mínima de Piso asociada a una Unidad (para expand)."""
    model_config = ConfigDict(from_attributes=True)

    Id: int
    NumeroPisoNombre: Optional[str] = None
    Checked: Optional[bool] = None

    # ✅ nuevos (para expand)
    DivisionId: Optional[int] = None
    Origen: Optional[str] = None  # 'pisos' | 'areas'
    Prio: Optional[int] = None

    Areas: List["AreaDTO"] = Field(default_factory=list)

class AreaDTO(BaseModel):
    """Proyección mínima de Área asociada a una Unidad."""
    model_config = ConfigDict(from_attributes=True)

    Id: int
    Nombre: Optional[str] = None
    PisoId: Optional[int] = None


# --------- Filtros / Patch ---------

class UnidadFilterDTO(BaseModel):
    """Filtro usado por list_filter en UnidadService."""
    model_config = ConfigDict(from_attributes=True)

    Unidad: Optional[str] = None
    userId: Optional[str] = None
    InstitucionId: Optional[int] = None
    ServicioId: Optional[int] = None
    RegionId: Optional[int] = None

    Active: Optional[int] = None


class UnidadPatchDTO(BaseModel):
    """
    Placeholder para compatibilidad de imports (router).
    Ajusta campos si necesitas PATCH real.
    """
    model_config = ConfigDict(from_attributes=True)
    # Define aquí campos opcionales si luego implementas PATCH.


# --------- DTOs principales ---------

class UnidadDTO(BaseModel):
    """
    DTO de detalle de Unidad. Coincide con el mapeo que hace UnidadService._map_unidad_to_dto.
    """
    model_config = ConfigDict(from_attributes=True)

    Id: int
    OldId: Optional[int] = None
    Nombre: Optional[str] = None

    ServicioId: int
    ServicioNombre: Optional[str] = None
    InstitucionNombre: Optional[str] = None

    Active: Union[str, int]  # en tu service envías "1"/"0"
    Funcionarios: Optional[int] = 0
    ReportaPMG: bool = False
    IndicadorEE: bool = False
    AccesoFactura: Union[int, str] = 0  # a veces string en listDTO

    InstitucionResponsableId: Optional[int] = None
    ServicioResponsableId: Optional[int] = None
    OrganizacionResponsable: Optional[str] = None

    # Si en algún momento pasas un objeto Servicio real, puedes tiparlo mejor
    Servicio: Optional[Any] = None

    Inmuebles: List[InmuebleTopDTO] = []
    Pisos: List[pisoDTO] = []
    Areas: List[AreaDTO] = []
    TipoUsoId: Optional[int] = None
    SuperficieM2: Optional[float] = None
    TipoPropiedadId: Optional[int] = None
    NumeroRol: Optional[str] = None
    NoPoseeRol: bool = False
    AnioConstruccion: Optional[int] = None
    OtrosColaboradores: Optional[int] = None

    AccesoFacturaAgua: bool = False

    ConsumeElectricidad: bool = False
    ComparteMedidorElectricidad: bool = False
    ConsumeGas: bool = False
    ComparteMedidorGas: bool = False
    ConsumeAgua: bool = False
    ComparteMedidorAgua: bool = False

class UnidadSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    ServicioId: Optional[int] = None
    Active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

class UnidadListDTO(BaseModel):
    """
    DTO de listado de Unidades. Coincide con _map_unidad_to_listdto.
    """
    model_config = ConfigDict(from_attributes=True)

    Id: int
    OldId: Optional[int] = None
    Nombre: Optional[str] = None

    Ubicacion: Optional[str] = None

    InstitucionId: int
    InstitucionNombre: Optional[str] = ""
    ServicioId: int
    ServicioNombre: Optional[str] = ""

    Active: Union[str, int]
    Funcionarios: Optional[int] = 0
    ReportaPMG: bool = False
    IndicadorEE: bool = False
    AccesoFactura: Union[str, int] = "0"

    InstitucionResponsableId: Optional[int] = None
    InstitucionResponsableNombre: Optional[str] = None
    ServicioResponsableId: Optional[int] = None
    ServicioResponsableNombre: Optional[str] = None
    OrganizacionResponsable: Optional[str] = None
    TipoUsoId: Optional[int] = None
    SuperficieM2: Optional[float] = None
    TipoPropiedadId: Optional[int] = None
    NumeroRol: Optional[str] = None
    NoPoseeRol: bool = False
    AnioConstruccion: Optional[int] = None
    OtrosColaboradores: Optional[int] = None

    AccesoFacturaAgua: bool = False

    ConsumeElectricidad: bool = False
    ComparteMedidorElectricidad: bool = False
    ConsumeGas: bool = False
    ComparteMedidorGas: bool = False
    ConsumeAgua: bool = False
    ComparteMedidorAgua: bool = False

# --------- NUEVOS DTOs: bulk-link / expand ---------

class LinkInmueblesRequest(BaseModel):
    """Body para vincular inmuebles a una unidad (bulk)."""
    inmuebles: List[int] = Field(..., min_items=1)


class LinkResult(BaseModel):
    created: List[int] = []
    skipped: List[int] = []
    not_found: List[int] = []
    deleted: List[int] = []  # solo se usa en modo sync


class UnidadWithInmueblesDTO(UnidadDTO):
    """Unidad + inmuebles con árbol completo."""
    InmueblesDetallados: List[InmuebleDTO] = Field(default_factory=list)

    # ✅ nuevo: división principal derivada
    Division: Optional["UnidadDivisionDTO"] = None
# =====================================================================
# ✅ NUEVO: DTO DE UPDATE (para Swagger + edición de campos)
# - Lo usamos en PUT /unidades/{id}
# - Todos los campos opcionales para poder mandar solo lo que cambia.
# - Tipamos Inmuebles según la estructura que tu service recorre.
# =====================================================================

Boolish = Union[int, bool, str]


class UnidadUpdateAreaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: Optional[int] = None


class UnidadUpdatePisoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: Optional[int] = None
    Areas: List[UnidadUpdateAreaDTO] = Field(default_factory=list)


class UnidadUpdateEdificioDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: Optional[int] = None
    Pisos: List[UnidadUpdatePisoDTO] = Field(default_factory=list)


class UnidadUpdateInmuebleRootDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: Optional[int] = None
    Edificios: List[UnidadUpdateEdificioDTO] = Field(default_factory=list)

class UnidadDivisionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Id: Optional[int] = None
    Origen: Optional[str] = None  # 'pisos' | 'areas'

class UnidadUpdateDTO(BaseModel):
    """
    Body de update. Swagger mostrará TODOS estos campos como editables.
    OJO: no incluimos CreatedAt/UpdatedAt/Version/CreatedBy/ModifiedBy/Id.
    """
    model_config = ConfigDict(from_attributes=True)

    # Estado (activar/desactivar)
    Active: Optional[Boolish] = None

    # Datos base
    OldId: Optional[int] = None
    Nombre: Optional[str] = None
    ServicioId: Optional[int] = None

    # Configuración / flags
    ChkNombre: Optional[int] = None
    AccesoFactura: Optional[Boolish] = None
    ReportaPMG: Optional[bool] = None
    IndicadorEE: Optional[bool] = None
    Funcionarios: Optional[int] = None

    # Responsables
    InstitucionResponsableId: Optional[int] = None
    ServicioResponsableId: Optional[int] = None
    OrganizacionResponsable: Optional[str] = None

    # Relaciones (solo si quieres que el PUT pueda resync de relaciones)
    Inmuebles: Optional[List[UnidadUpdateInmuebleRootDTO]] = None
    TipoUsoId: Optional[int] = None
    SuperficieM2: Optional[float] = None
    TipoPropiedadId: Optional[int] = None
    NumeroRol: Optional[str] = None
    NoPoseeRol: bool = False
    AnioConstruccion: Optional[int] = None
    OtrosColaboradores: Optional[int] = None

    AccesoFacturaAgua: bool = False

    ConsumeElectricidad: bool = False
    ComparteMedidorElectricidad: bool = False
    ConsumeGas: bool = False
    ComparteMedidorGas: bool = False
    ConsumeAgua: bool = False
    ComparteMedidorAgua: bool = False

# Export explícito por claridad
__all__ = [
    "InmuebleTopDTO",
    "pisoDTO",
    "AreaDTO",
    "UnidadFilterDTO",
    "UnidadPatchDTO",
    "UnidadDTO",
    "UnidadListDTO",
    "LinkInmueblesRequest",
    "LinkResult",
    "UnidadWithInmueblesDTO",

    # ✅ nuevo
    "UnidadUpdateDTO",
    "UnidadUpdateInmuebleRootDTO",
    "UnidadUpdateEdificioDTO",
    "UnidadUpdatePisoDTO",
    "UnidadUpdateAreaDTO",
    "UnidadDivisionDTO",
]
