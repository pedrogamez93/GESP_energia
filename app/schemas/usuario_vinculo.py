# app/schemas/usuario_vinculo.py
from pydantic import BaseModel
from typing import List

class IdsPayload(BaseModel):
    Ids: List[int] = []

class UserDetailDTO(BaseModel):
    Id: str
    UserName: str | None = None
    Email: str | None = None
    Active: bool | None = None
    Roles: List[str] = []
    InstitucionIds: List[int] = []
    ServicioIds: List[int] = []
    DivisionIds: List[int] = []
    UnidadIds: List[int] = []

    class Config:
        from_attributes = True
