from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserModel(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    role: Literal["cliente", "admin", "administrador"] = "cliente"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "carlos.rodriguez",
                "email": "carlos.rodriguez@example.com",
                "password": "contraseña_segura",
                "full_name": "Carlos Rodríguez",
                "role": "cliente",
            }
        }
    )


class UserUpdateModel(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=40)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=12, max_length=128)
    full_name: Optional[str] = Field(None, min_length=2, max_length=120)
    role: Optional[Literal["cliente", "admin", "administrador"]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Carlos A. Rodríguez",
                "role": "administrador",
            }
        }
    )
