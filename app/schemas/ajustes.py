# app/schemas/ajustes.py
from pydantic import BaseModel, ConfigDict
from typing import Optional

class AjusteDTO(BaseModel):
    Id: int
    EditUnidadPMG: bool
    DeleteUnidadPMG: bool
    ComprasServicio: bool
    CreateUnidadPMG: bool
    ActiveAlcanceModule: bool
    model_config = ConfigDict(from_attributes=True)

class AjustePatchDTO(BaseModel):
    EditUnidadPMG: Optional[bool] = None
    DeleteUnidadPMG: Optional[bool] = None
    ComprasServicio: Optional[bool] = None
    CreateUnidadPMG: Optional[bool] = None
    ActiveAlcanceModule: Optional[bool] = None
