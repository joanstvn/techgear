from fastapi import APIRouter, Depends, HTTPException, status

from src.database.database import users_collection
from src.models.user import UserModel, UserUpdateModel
from src.utils.mongo import validate_object_id
from src.utils.security import hash_password, require_admin, serialize_user

router = APIRouter()


def _ensure_unique_fields(user_data: dict, excluded_id=None) -> None:
    """Valida que el username y el email no estén registrados por otro usuario."""
    for field in ("username", "email"):
        value = user_data.get(field)
        if not value:
            continue
        query = {field: value}
        if excluded_id is not None:
            query["_id"] = {"$ne": excluded_id}
        if users_collection.find_one(query):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El {field} '{value}' ya está registrado",
            )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo usuario",
    description="Registra un nuevo usuario en la base de datos. Requiere rol de administrador.",
)
def create_user(user: UserModel, current_user: dict = Depends(require_admin)):
    user_dict = user.model_dump()
    user_dict["email"] = user_dict["email"].lower()
    _ensure_unique_fields(user_dict)
    user_dict["password"] = hash_password(user_dict["password"])

    result = users_collection.insert_one(user_dict)
    created_user = users_collection.find_one({"_id": result.inserted_id})
    return serialize_user(created_user)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Listar todos los usuarios",
    description="Devuelve la lista completa de usuarios registrados. Requiere rol de administrador.",
)
def list_users(current_user: dict = Depends(require_admin)):
    users = list(users_collection.find())
    return [serialize_user(u) for u in users]


@router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Obtener un usuario por ID",
    description="Busca un usuario por su identificador único de MongoDB. Requiere rol de administrador.",
)
def get_user(id: str, current_user: dict = Depends(require_admin)):
    obj_id = validate_object_id(id)
    user = users_collection.find_one({"_id": obj_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID '{id}' no encontrado",
        )
    return serialize_user(user)


@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Actualizar un usuario",
    description="Actualiza uno o varios campos de un usuario existente. Requiere rol de administrador.",
)
def update_user(
    id: str,
    user_data: UserUpdateModel,
    current_user: dict = Depends(require_admin),
):
    obj_id = validate_object_id(id)
    update_data = user_data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar al menos un campo para actualizar",
        )

    if "email" in update_data:
        update_data["email"] = update_data["email"].lower()
    _ensure_unique_fields(update_data, excluded_id=obj_id)

    if "password" in update_data:
        update_data["password"] = hash_password(update_data["password"])

    result = users_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID '{id}' no encontrado",
        )

    updated_user = users_collection.find_one({"_id": obj_id})
    return serialize_user(updated_user)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar un usuario",
    description="Elimina un usuario existente por su ID. Requiere rol de administrador.",
)
def delete_user(id: str, current_user: dict = Depends(require_admin)):
    obj_id = validate_object_id(id)
    result = users_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID '{id}' no encontrado",
        )
    return {"message": f"Usuario con ID '{id}' eliminado correctamente"}
