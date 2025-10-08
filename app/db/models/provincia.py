from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Provincia(Base):
    __tablename__ = "Provincias"

    Id = Column(Integer, primary_key=True, index=True)
    RegionId = Column(Integer, ForeignKey("Regiones.Id"), nullable=False)
    Nombre = Column(String, nullable=False)

    # Relaciones
    Region = relationship("Region", back_populates="Provincias")
    Comunas = relationship("Comuna", back_populates="Provincia")
    Inmuebles = relationship("Division", back_populates="Provincia")
    Direcciones = relationship("Direccion", back_populates="Provincia")
