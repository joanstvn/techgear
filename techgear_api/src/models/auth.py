from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginModel(BaseModel):
    username: str = Field(
        ...,
        description="Nombre de usuario o correo electrónico registrado",
    )
    password: str = Field(..., description="Contraseña del usuario")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "admin",
                "password": "admin123",
            }
        }
    )


class RegisterModel(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)


class TokenModel(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": "6701f2a8b4c9d1e2f3a4b5c6",
                    "username": "admin",
                    "email": "admin@techgear.com",
                    "full_name": "Administrador TechGear",
                    "role": "administrador",
                },
            }
        }
    )
