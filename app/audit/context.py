# app/audit/context.py
from contextvars import ContextVar

# Metadatos del request disponibles en el contexto actual (los setea el middleware)
current_request_meta: ContextVar[dict] = ContextVar("current_request_meta", default={})
