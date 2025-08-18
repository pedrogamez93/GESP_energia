from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import auth, users, comunas, regiones, instituciones
from app.db.session import engine

try:
    from app.core.config import settings
    ALLOW_ORIGINS = getattr(settings, "CORS_ORIGINS", ["*"])
except Exception:
    ALLOW_ORIGINS = ["*"]

tags_metadata = [
    {"name": "Health", "description": "Endpoints de verificación."},
    {"name": "Auth", "description": "Autenticación y sesión."},
    {"name": "Users", "description": "Usuarios."},
    {"name": "Comunas", "description": "Comunas por región."},
    {"name": "Regiones", "description": "Regiones del país."},
    {"name": "Instituciones", "description": "Instituciones y asociaciones de usuarios."},
]

app = FastAPI(title="API GESP", version="1.0.0", openapi_tags=tags_metadata)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "API up"}

@app.get("/api/v1", tags=["Health"])
def api_v1_root():
    return {"status": "ok", "message": "API up"}

@app.get("/api/v1/health/db", tags=["Health"])
def health_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="DB unavailable")

# Incluye routers (cada uno ya define su prefix /api/v1/...)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(comunas.router)
app.include_router(regiones.router)
app.include_router(instituciones.router)
