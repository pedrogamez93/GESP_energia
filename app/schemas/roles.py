# app/schemas/roles.py
from pydantic import BaseModel
from typing import Optional, List

class RoleDTO(BaseModel):
    Id: str
    Name: Optional[str] = None
    NormalizedName: Optional[str] = None
    Nombre: Optional[str] = None
    class Config: from_attributes = True

class RoleCreate(BaseModel):
    Name: str

class RoleUpdate(BaseModel):
    Name: str

class UserRolesDTO(BaseModel):
    UserId: str
    Roles: List[str] = []
