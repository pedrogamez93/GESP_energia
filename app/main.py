# app/main.py
from app.api.v1 import tipos_equipos_calefaccion
from app.api.v1 import tipos_colectores
from app.api.v1 import energeticos
from app.services import tipos_luminarias
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from uuid import uuid4
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from starlette.responses import Response
import asyncio
import json
from hashlib import sha256
from urllib.parse import parse_qs

from app.db.session import engine

# ⬇️ importa y registra los listeners de auditoría al boot
from app.audit import hooks   # <-- ¡IMPORTANTE!

import logging
log = logging.getLogger("uvicorn.error")

# CORS
try:
    from app.core.config import settings
    ALLOW_ORIGINS = getattr(settings, "CORS_ORIGINS", ["*"])
except Exception:
    ALLOW_ORIGINS = ["*"]

# --- Importa routers explícitamente desde cada submódulo ---
from app.api.v1 import debug
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.usuarios import router as usuarios_router
from app.api.v1.comunas import router as comunas_router
from app.api.v1.regiones import router as regiones_router
from app.api.v1.instituciones import router as instituciones_router
from app.api.v1.servicios import router as servicios_router
from app.api.v1.unidades_medida import router as unidades_medida_router
from app.api.v1.energeticos import router as energeticos_router
from app.api.v1.empresas_distribuidoras import router as empresas_distribuidoras_router
from app.api.v1.roles import router as roles_router
from app.api.v1.divisiones import router as divisiones_router
from app.api.v1.edificios import router as edificios_router
from app.api.v1.equipos import router as equipos_router
from app.api.v1.tipos_luminarias import router as tipos_luminarias_router
from app.api.v1.tipos_equipos_calefaccion import router as tipos_equipos_calefaccion_router
from app.api.v1.sistemas import router as sistemas_router
from app.api.v1.modos_operacion import router as modos_operacion_router
from app.api.v1.tipos_edificios import router as tipos_edificios_router
from app.api.v1.entornos import router as entornos_router
from app.api.v1.inercia_termicas import router as inercia_termicas_router
from app.api.v1.tipo_agrupamientos import router as tipo_agrupamientos_router
from app.api.v1.tipo_tecnologias import router as tipo_tecnologias_router
from app.api.v1.tipos_colectores import router as tipos_colectores_router
from app.api.v1.catalogos_equipos import router as catalogos_equipos_router
from app.api.v1.medidores import router as medidores_router
from app.api.v1.medidores_inteligentes import router as medidores_inteligentes_router
from app.api.v1.numero_clientes import router as numero_clientes_router
from app.api.v1.tipos_tarifas import router as tipos_tarifas_router
from app.api.v1.documentos import router as documentos_router
from app.api.v1.plangestion import router as plangestion_router
from app.api.v1.inmuebles import router as inmuebles_router
from app.api.v1.pisos import router as pisos_router
from app.api.v1.areas import router as areas_router
from app.api.v1.direcciones import router as direcciones_router
from app.api.v1 import medidores_vinculos
from app.api.v1 import energetico_divisiones
from app.api.v1 import medidor_divisiones
from app.api.v1 import compras
from app.api.v1.ajustes import router as ajustes_router
from app.api.v1.frontis import router as frontis_router
from app.api.v1.reportes import router as reportes_router
from app.api.v1.parametros_medicion import router as parametros_medicion_router
from app.api.v1.provincia import router as provincias_router

from app.audit.context import current_request_meta

from app.api.v1 import division_sistemas                      
from app.api.v1 import tipo_equipo_calefaccion_energeticos
from app.api.v1 import division_sistemas_detalle

# --- OpenAPI tags (opcional, añade los que quieras mostrar en Swagger) ---
tags_metadata = [
    {"name": "Health", "description": "Endpoints de verificación."},
    {"name": "Auth", "description": "Autenticación y sesión."},
    {"name": "Users", "description": "Usuarios."},
    {"name": "Usuarios (admin)", "description": "Detalle y vínculos de usuarios (solo ADMIN)."},
    {"name": "Comunas", "description": "Comunas por región."},
    {"name": "Regiones", "description": "Regiones del país."},
    {"name": "Instituciones", "description": "Instituciones y asociaciones de usuarios."},
    {"name": "Unidades de medida", "description": "Catálogo de unidades (Nombre, Abrv)."},
    {"name": "Energéticos", "description": "Catálogo de energéticos, sus unidades de medida y asignación por división."},
    {"name": "Empresas distribuidoras", "description": "Catálogo de empresas distribuidoras y comunas asociadas."},
    {"name": "Divisiones", "description": "Divisiones y vistas relacionadas."},
    {"name": "Edificios", "description": "Edificios."},
    {"name": "Equipos", "description": "Equipos vinculados a divisiones."},
    {"name": "Luminarias", "description": "Tipos de luminarias."},
    {"name": "Equipos calefacción", "description": "Tipos de equipos de calefacción."},
    {"name": "Sistemas", "description": "Sistemas energéticos."},
    {"name": "Modo de operación", "description": "Modos de operación."},
    {"name": "Tipos de edificios", "description": "Catálogo de tipos de edificios."},
    {"name": "Entornos", "description": "Entornos."},
    {"name": "Inercia térmica", "description": "Catálogo de inercia térmica."},
    {"name": "Tipos de agrupamientos", "description": "Catálogo."},
    {"name": "Tecnologías", "description": "Tipos de tecnologías."},
    {"name": "Colectores", "description": "Tipos de colectores."},
    {"name": "Catálogos equipos", "description": "Varios catálogos para equipos."},
    {"name": "Medidores", "description": "Medidores y relaciones."},
    {"name": "Medidores inteligentes", "description": "Smart meters."},
    {"name": "Números de cliente", "description": "Números de cliente y datos asociados."},
    {"name": "Tipos de tarifa", "description": "Catálogo de tarifas eléctricas."},
    {"name": "Documentos", "description": "Gestión y listado de documentos."},
    {"name": "Plan de Gestión", "description": "Acciones, tareas y reportes del plan de gestión."},
    {"name": "Inmuebles", "description": "Inmuebles (basado en Divisiones + Direcciones)."},
    {"name": "Pisos", "description": "Gestión de pisos por inmueble (División)."},
    {"name": "Áreas", "description": "Gestión de áreas por piso."},
    {"name": "Direcciones", "description": "Catálogo/CRUD de direcciones y resolución exacta."},
    {"name": "Parámetros de medición", "description": "Catálogo y CRUD de parámetros (vinculados a UM)."},
]

# --- App ---
app = FastAPI(title="API GESP", version="1.0.0", openapi_tags=tags_metadata)

# Respeta X-Forwarded-For / X-Forwarded-Proto si estás detrás de Nginx/ALB
app.add_middleware(ProxyHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== Auditoría: captura body en métodos de escritura, con redacción ======
SENSITIVE_KEYS = {
    "password", "pass", "contrasena", "contraseña",
    "token", "access_token", "refresh_token", "authorization",
    "api_key", "secret", "client_secret", "clave", "key"
}
MAX_BODY_LOG = 64 * 1024  # 64 KB
EXCLUDED_PATHS = {"/api/v1/auth/login"}  # evita guardar credenciales en login

def _redact(value):
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    s = str(value)
    return s if len(s) <= 2 else s[:2] + "***" + s[-2:]

def _redact_json(obj):
    if isinstance(obj, dict):
        return {k: ("***" if k.lower() in SENSITIVE_KEYS else _redact_json(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_json(v) for v in obj]
    return obj

# --- Middleware de request: adjunta metadatos + body redacted a request.state.audit_meta ---
@app.middleware("http")
@app.middleware("http")
async def attach_request_meta(request: Request, call_next):
    xff = request.headers.get("x-forwarded-for")
    ip = (xff.split(",")[0].strip() if xff else request.client.host)

    meta = {
        "ip": ip,
        "user_agent": request.headers.get("user-agent"),
        "method": request.method,
        "path": request.url.path,
        "request_id": str(uuid4()),
        "status_code": 200,
    }

    # 👇 LOG del Authorization (redactado) solo para /api/v1/inmuebles
    if request.url.path.startswith("/api/v1/inmuebles"):
        auth = request.headers.get("authorization")
        def redact(a: str | None):
            if not a:
                return None
            # ejemplo: "Bearer eyJ***9Q"
            return a[:10] + "***" + a[-2:] if len(a) > 12 else "***"
        log.info(f"[AUTH-CHK] path=%s auth=%s", request.url.path, redact(auth))

    # --- (tu lógica de auditoría que ya tenías) ---
    capture_body = (
        request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and request.url.path not in {"/api/v1/auth/login"}
    )
    body_json_str = None
    body_hash = None
    if capture_body:
        body_bytes = await request.body()
        async def _receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        request._receive = _receive
        if body_bytes:
            sample = body_bytes[:(64 * 1024)]
            from json import loads, dumps
            from hashlib import sha256
            from urllib.parse import parse_qs
            body_hash = sha256(body_bytes).hexdigest()
            ctype = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
            try:
                if "application/json" in ctype:
                    parsed = loads(sample.decode("utf-8"))
                    body_json_str = dumps(parsed, ensure_ascii=False)
                elif "application/x-www-form-urlencoded" in ctype:
                    parsed_raw = parse_qs(sample.decode("utf-8"))
                    parsed = {k: (v[0] if isinstance(v, list) and v else v) for k, v in parsed_raw.items()}
                    body_json_str = dumps(parsed, ensure_ascii=False)
                else:
                    body_json_str = json.dumps({"_raw_preview": sample.decode("utf-8", errors="ignore")}, ensure_ascii=False)
            except Exception:
                body_json_str = json.dumps({"_raw_preview": sample.decode("utf-8", errors="ignore")}, ensure_ascii=False)

    meta["request_body_json"] = body_json_str
    meta["request_body_sha256"] = body_hash

    request.state.audit_meta = meta
    current_request_meta.set(meta)

    try:
        resp = await call_next(request)
        meta["status_code"] = resp.status_code
        return resp
    except asyncio.CancelledError:
        meta["status_code"] = 499
        return Response(status_code=499, content=b"Client Closed Request")

# --- Health ---
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "API up"}

@app.get("/api/v1", tags=["Health"])
def api_v1_root():
    return {"status": "ok", "message": "API v1 up"}

@app.get("/api/v1/health/db", tags=["Health"])
def health_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="DB unavailable")

# --- Routers ---
app.include_router(debug.dbg)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(usuarios_router)
app.include_router(comunas_router)
app.include_router(regiones_router)
app.include_router(instituciones_router)
app.include_router(servicios_router)
app.include_router(unidades_medida_router)
app.include_router(energeticos_router)
app.include_router(empresas_distribuidoras_router)
app.include_router(roles_router)
app.include_router(divisiones_router)
app.include_router(edificios_router)
app.include_router(equipos_router)
app.include_router(tipos_luminarias_router)
app.include_router(tipos_equipos_calefaccion_router)
app.include_router(sistemas_router)
app.include_router(modos_operacion_router)
app.include_router(tipos_edificios_router)
app.include_router(entornos_router)
app.include_router(inercia_termicas_router)
app.include_router(tipo_agrupamientos_router)
app.include_router(tipo_tecnologias_router)
app.include_router(tipos_colectores_router)
app.include_router(catalogos_equipos_router)
app.include_router(medidores_router)
app.include_router(medidores_inteligentes_router)
app.include_router(numero_clientes_router)
app.include_router(tipos_tarifas_router)
app.include_router(medidores_vinculos.router)
app.include_router(energetico_divisiones.router)
app.include_router(medidor_divisiones.router)
app.include_router(compras.router)
app.include_router(documentos_router)
app.include_router(plangestion_router)
app.include_router(inmuebles_router)
app.include_router(pisos_router)
app.include_router(areas_router)
app.include_router(direcciones_router)
app.include_router(ajustes_router)
app.include_router(frontis_router)
app.include_router(reportes_router)
app.include_router(parametros_medicion_router)
app.include_router(provincias_router)
app.include_router(division_sistemas.router)                 
app.include_router(tipo_equipo_calefaccion_energeticos.router) 
app.include_router(division_sistemas_detalle.router)
app.include_router(tipos_luminarias.router)           # ya trae /api/v1/tipos-luminarias
app.include_router(tipos_equipos_calefaccion.router)  # ya trae /api/v1/tipos-equipos-calefaccion
app.include_router(tipos_colectores.router)           # ya trae /api/v1/tipos-colectores
app.include_router(energeticos.router)                # ya trae /api/v1/energeticos