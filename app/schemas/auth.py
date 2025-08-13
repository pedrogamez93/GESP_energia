from pydantic import BaseModel, ConfigDict

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str | None = None
    email: str | None = None
    nombres: str | None = None
    apellidos: str | None = None
    roles: list[str] = []

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
