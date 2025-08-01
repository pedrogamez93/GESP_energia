from fastapi import FastAPI
from app.api.v1 import users

app = FastAPI(title="FastAPI Migrated Project")

app.include_router(users.router, prefix="/users", tags=["Users"])
