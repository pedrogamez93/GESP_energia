# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import auth, users, comunas, regiones
from app.db.session import engine

# (opcional) si tienes settings, usa .env; si no, deja la lista fija
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
]

app = FastAPI(
    title="API GESP",
    version="1.0.0",
    openapi_tags=tags_metadata,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,  # en prod: define CORS_ORIGINS en .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Health ----
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "API up"}

@app.get("/api/v1", tags=["Health"])
def api_v1_root():
    return {"status": "ok", "message": "API v1 up"}

# Health DB simple: SELECT 1 (sin get_db)
@app.get("/api/v1/health/db", tags=["Health"])
def health_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="DB unavailable")

# ---- Routers v1 ----
app.include_router(auth.router,    prefix="/api/v1", tags=["Auth"])
app.include_router(users.router,   prefix="/api/v1", tags=["Users"])
app.include_router(comunas.router, prefix="/api/v1", tags=["Comunas"])
app.include_router(regiones.router, prefix="/api/v1", tags=["Regiones"])
