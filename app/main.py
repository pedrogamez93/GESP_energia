from fastapi import FastAPI
from app.api.v1 import auth  # <-- importa el router

app = FastAPI(title="GESP Energia API")

# La ruta final será: POST /api/v1/auth/login
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "API up"}

@app.get("/api/v1", tags=["Health"])
def api_v1_root():
    return {"status": "ok", "message": "API up"}

# imprime rutas al arrancar (útil para depurar)
@app.on_event("startup")
async def show_routes():
    for r in app.router.routes:
        methods = ",".join(sorted(getattr(r, "methods", {"GET"})))
        print("ROUTE:", r.path, methods)
