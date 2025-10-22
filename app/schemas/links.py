from pydantic import BaseModel, conlist

class LinkUnidades(BaseModel):
    unidades: conlist(int, min_length=1)   # lista de UnidadId
