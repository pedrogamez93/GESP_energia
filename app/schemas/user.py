from typing import Optional, Union
from pydantic import BaseModel, EmailStr, Field, AliasChoices
from pydantic import ConfigDict

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserOut(BaseModel):
    # Acepta Id/id (string o int si tu PK es UNIQUEIDENTIFIER)
    id: Union[int, str] = Field(validation_alias=AliasChoices("id", "Id"))
    # Acepta Email/email
    email: EmailStr = Field(validation_alias=AliasChoices("email", "Email"))
    # Acepta FullName/full_name (puede venir nulo)
    full_name: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("full_name", "FullName")
    )

    # Pydantic v2
    model_config = ConfigDict(
        from_attributes=True,   # permite construir desde objetos ORM
        populate_by_name=True   # habilita validation_alias/AliasChoices
    )
