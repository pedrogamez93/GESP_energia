# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # si ya usas CORS_ORIGINS, déjalo; si no, comenta esta línea
    CORS_ORIGINS: List[str] = ["*"]

    # 👇 NUEVO: para los adjuntos de Documentos
    FILES_DIR: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",          # para que no falle si agregas alguna var extra
    )

settings = Settings()
