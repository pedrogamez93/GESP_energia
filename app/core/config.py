# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 🔥 CORS CONFIG REAL (reemplaza el ["*"])
    # Estos son los orígenes permitidos para llamar la API.
    CORS_ORIGINS: List[str] = [
        "http://localhost:4200",
        "http://energia.metasoft-testing.com",
        "https://energia.metasoft-testing.com",
        "https://api-energia.metasoft-testing.com",
    ]

    # 👇 (Opcional) Si algún día quieres permitir TODOS los subdominios:
    # CORS_ORIGINS_REGEX: Optional[str] = r"^https?://(localhost:4200|.*\.metasoft-testing\.com)$"

    # 📁 Ruta base donde guardas adjuntos de Documentos
    FILES_DIR: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  # no falla si agregas más variables en .env
    )


settings = Settings()
