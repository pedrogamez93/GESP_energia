from sqlalchemy.orm import declarative_base

Base = declarative_base()

from app.db.models.unidad import Unidad                # noqa: F401
from app.db.models.unidad_inmueble import UnidadInmueble  # noqa: F401
from app.db.models.division import Division            # noqa: F401