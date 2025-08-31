# app/main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from uuid import uuid4
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.db.session import engine

# CORS
try:
    from app.core.config import settings
    ALLOW_ORIGINS = getattr(settings, "CORS_ORIGINS", ["*"])
except Exception:
    ALLOW_ORIGINS = ["*"]

# --- Importa routers explícitamente desde cada submódulo ---
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
# (añadido)
app.add_middleware(ProxyHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Middleware de request: adjunta metadatos a request.state.audit_meta (añadido) ---
@app.middleware("http")
async def attach_request_meta(request: Request, call_next):
    xff = request.headers.get("x-forwarded-for")
    ip = (xff.split(",")[0].strip() if xff else request.client.host)
    request.state.audit_meta = {
        "ip": ip,
        "user_agent": request.headers.get("user-agent"),
        "method": request.method,
        "path": request.url.path,
        "request_id": str(uuid4()),
    }
    resp = await call_next(request)
    # completa metadatos con status_code una vez producido el response
    request.state.audit_meta["status_code"] = resp.status_code
    return resp

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
