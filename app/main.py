from fastapi import FastAPI
from app.api.v1 import auth  

app = FastAPI(title="GESP Energia API")

# Prefijo de versión
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "API up"}

@app.get("/api/v1", tags=["Health"])
def api_v1_root():
    return {"status": "ok", "message": "API up"}

