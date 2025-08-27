from pydantic import BaseModel
from typing import Optional

class SelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config: from_attributes = True
