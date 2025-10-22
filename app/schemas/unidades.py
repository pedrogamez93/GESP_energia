from typing import Optional
from pydantic import BaseModel

class UnidadBrief(BaseModel):
    id: int
    nombre: Optional[str] = None
    servicio_id: Optional[int] = None
    activo: Optional[bool] = None
    # agrega campos si los necesitas luego (ej. codigo, numero_serie, etc.)
