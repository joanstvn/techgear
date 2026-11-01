from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.database.database import users_collection
from src.models.auth import (
    LoginModel,
    RegisterModel,
    TokenModel,
)
from src.utils.security import (
    JWT_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    serialize_user,
    hash_password,
    verify_password,
)

router = APIRouter()


class MessageModel(BaseModel):
    message: str


@router.post(
    "/register",
    response_model=MessageModel,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una cuenta de cliente",
)
def register(data: RegisterModel):
    username = data.username.strip()
    email = str(data.email).lower()
    if users_collection.find_one({"$or": [{"username": username}, {"email": email}]}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese usuario o correo ya está registrado.",
        )

    user = {
        "username": username,
        "email": email,
        "full_name": data.full_name.strip(),
        "password": hash_password(data.password),
        # El registro público nunca puede crear administradores.
        "role": "cliente",
    }
    users_collection.insert_one(user)
    return {"message": "Tu cuenta se creó correctamente. Ya puedes iniciar sesión."}


@router.post(
    "/login",
    response_model=TokenModel,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión",
    description="Valida las credenciales del usuario y devuelve un token JWT de acceso.",
)
def login(credentials: LoginModel):
    identifier = credentials.username.strip()
    user = users_collection.find_one(
        {
            "$or": [
                {"username": identifier},
                {"email": identifier.lower()},
            ]
        }
    )

    if not user or not verify_password(credentials.password, user.get("password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRE_MINUTES * 60,
        "user": serialize_user(user),
    }


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Obtener el usuario autenticado",
    description="Devuelve los datos del usuario asociado al token JWT enviado.",
)
def read_current_user(current_user: dict = Depends(get_current_user)):
    return serialize_user(current_user)
