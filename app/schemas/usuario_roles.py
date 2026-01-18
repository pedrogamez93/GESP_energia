# app/schemas/usuario_roles.py
from pydantic import BaseModel, Field
from typing import List

class RolesPayload(BaseModel):
    roles: List[str] = Field(default_factory=list)