# app/core/app_validation.py

from __future__ import annotations
import os
from fastapi import Request

def _load_app_key_config() -> tuple[str | None, str | None]:
    """
    Equivalente a:
      HeaderKeyName = _configuration["application-key:header"]
      HeaderKeyValue = _configuration["application-key:value"]
    Soportamos:
      - Variables de entorno: APPLICATION_KEY_HEADER / APPLICATION_KEY_VALUE
      - settings.application_key.header / settings.application_key.value (si existe)
      - settings.APPLICATION_KEY_HEADER / settings.APPLICATION_KEY_VALUE (si existe)
    """
    header = os.getenv("APPLICATION_KEY_HEADER")
    value = os.getenv("APPLICATION_KEY_VALUE")

    try:
        from app.core.config import settings  # tu settings existente
        # intents comunes
        header = getattr(settings, "APPLICATION_KEY_HEADER", header) or header
        value  = getattr(settings, "APPLICATION_KEY_VALUE",  value)  or value

        # posible objeto/dict anidado application_key = { header, value }
        ak = getattr(settings, "application_key", None)
        if ak and not header:
            header = getattr(ak, "header", None) or (ak.get("header") if isinstance(ak, dict) else None)
        if ak and not value:
            value  = getattr(ak, "value",  None) or (ak.get("value")  if isinstance(ak, dict) else None)
    except Exception:
        # si settings no existe o no tiene esas claves, seguimos con env vars
        pass

    return header, value

def is_app_validate(request: Request) -> bool:
    """
    Replica ApplicationValidation de .NET:
    - Lee nombre del header y valor esperado de configuración
    - Valida que el header exista y coincida exactamente
    - Devuelve True/False (quien llame decide si retorna 401)
    """
    header_name, expected_value = _load_app_key_config()
    if not header_name or not expected_value:
        # Si no hay config, por compatibilidad puedes elegir:
        # - devolver False (bloquea) o
        # - devolver True (permite). En .NET la config siempre estaba.
        # Dejamos "False" para ser seguros; si prefieres, cambia a True.
        return False

    incoming = request.headers.get(header_name)
    if not incoming:
        return False
    return incoming == expected_value