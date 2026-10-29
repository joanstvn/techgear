import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.database.database import users_collection
from src.utils.mongo import serialize_doc

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Configuración del token JWT
JWT_SECRET = os.getenv("JWT_SECRET", "techgear-dev-secret-cambia-esto-en-produccion")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# Parámetros del algoritmo de hashing de contraseñas (PBKDF2-HMAC-SHA256)
PASSWORD_HASH_ITERATIONS = 260_000
PASSWORD_HASH_PREFIX = "pbkdf2_sha256"

# Esquema de autenticación Bearer para Swagger y dependencias
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Genera un hash seguro de la contraseña usando PBKDF2-HMAC-SHA256."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}${salt}${digest.hex()}"


def verify_password(plain_password: str, stored_password: str) -> bool:
    """Verifica una contraseña contra un hash PBKDF2 o un valor en texto plano."""
    if not stored_password:
        return False

    # Compatibilidad con contraseñas antiguas guardadas en texto plano
    if not stored_password.startswith(f"{PASSWORD_HASH_PREFIX}$"):
        return hmac.compare_digest(plain_password, stored_password)

    try:
        _, iterations, salt, expected_hash = stored_password.split("$", 3)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(digest.hex(), expected_hash)


def create_access_token(user: dict) -> str:
    """Crea un token JWT firmado con los datos básicos del usuario."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["_id"]),
        "username": user.get("username"),
        "role": user.get("role"),
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decodifica y valida un token JWT, lanzando HTTPException si no es válido."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token ha expirado, inicia sesión nuevamente",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """Obtiene el usuario autenticado a partir del token Bearer de la petición."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere autenticación para acceder a este recurso",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")

    if not user_id or not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario del token ya no existe",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Restringe el acceso a usuarios con rol de administrador."""
    role = str(current_user.get("role", "")).strip().lower()
    if role not in {"admin", "administrador"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador para esta acción",
        )
    return current_user


def serialize_user(doc: dict) -> dict:
    """Convierte un documento de usuario y elimina la contraseña de la respuesta."""
    data = serialize_doc(doc)
    data.pop("password", None)
    return data
