# app/schemas/medidor.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List

# =========================
# Medidores (dbo.Medidores)
# =========================

class MedidorListDTO(BaseModel):
    Id: int
    Numero: Optional[str] = None
    NumeroClienteId: int
    Fases: int = 0
    Smart: bool = False
    Compartido: bool = False
    DivisionId: Optional[int] = None
    Factura: Optional[bool] = None
    Chilemedido: bool = False
    DeviceId: Optional[int] = None
    MedidorConsumo: bool = False
    Active: bool = True

    class Config:
        from_attributes = True

class MedidorDTO(MedidorListDTO):
    CreatedAt: Optional[str] = None
    UpdatedAt: Optional[str] = None
    Version: Optional[int] = None

class MedidorCreate(BaseModel):
    Numero: Optional[str] = None
    NumeroClienteId: int
    Fases: int = 0
    Smart: bool = False
    Compartido: bool = False
    DivisionId: Optional[int] = None
    Factura: Optional[bool] = None
    Chilemedido: bool = False
    DeviceId: Optional[int] = None
    MedidorConsumo: bool = False

class MedidorUpdate(BaseModel):
    Numero: Optional[str] = None
    NumeroClienteId: Optional[int] = None
    Fases: Optional[int] = None
    Smart: Optional[bool] = None
    Compartido: Optional[bool] = None
    DivisionId: Optional[int] = None
    Factura: Optional[bool] = None
    Chilemedido: Optional[bool] = None
    DeviceId: Optional[int] = None
    MedidorConsumo: Optional[bool] = None
    Active: Optional[bool] = None


# ======================================
# Medidores Inteligentes (dbo.MedidoresInteligentes)
# ======================================

class MedidorInteligenteDTO(BaseModel):
    Id: int
    ChileMedidoId: int
    # si tus endpoints devuelven vínculos, los dejamos aquí:
    DivisionIds: List[int] = []
    EdificioIds: List[int] = []
    ServicioIds: List[int] = []

    class Config:
        from_attributes = True

class MedidorInteligenteCreate(BaseModel):
    ChileMedidoId: int
    # opcionalmente permitir crear con vínculos:
    DivisionIds: List[int] = []
    EdificioIds: List[int] = []
    ServicioIds: List[int] = []

class MedidorInteligenteUpdate(BaseModel):
    ChileMedidoId: Optional[int] = None
    Active: Optional[bool] = None
    # si algún endpoint admite reemplazo masivo de vínculos:
    DivisionIds: Optional[List[int]] = None
    EdificioIds: Optional[List[int]] = None
    ServicioIds: Optional[List[int]] = None


# Payload genérico para endpoints que reciben listas de Ids
class IdsPayload(BaseModel):
    Ids: List[int] = []
