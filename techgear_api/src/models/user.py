from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class UserModel(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    role: str

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
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Carlos A. Rodríguez",
                "role": "administrador",
            }
        }
    )
