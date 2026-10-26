from fastapi import APIRouter, HTTPException, status

from src.database.database import products_collection
from src.models.product import ProductModel, ProductUpdateModel
from src.utils.mongo import serialize_doc, validate_object_id

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo producto",
    description="Registra un nuevo producto en la base de datos.",
)
def create_product(product: ProductModel):
    product_dict = product.model_dump()
    result = products_collection.insert_one(product_dict)
    created_product = products_collection.find_one({"_id": result.inserted_id})
    return serialize_doc(created_product)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Listar todos los productos",
    description="Devuelve la lista completa de productos.",
)
def list_products():
    products = list(products_collection.find())
    return [serialize_doc(p) for p in products]


@router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Obtener un producto por ID",
    description="Busca un producto por su identificador único de MongoDB.",
)
def get_product(id: str):
    obj_id = validate_object_id(id)
    product = products_collection.find_one({"_id": obj_id})
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID '{id}' no encontrado",
        )
    return serialize_doc(product)


@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Actualizar un producto",
    description="Actualiza uno o varios campos de un producto existente.",
)
def update_product(id: str, product_data: ProductUpdateModel):
    obj_id = validate_object_id(id)
    update_data = product_data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar al menos un campo para actualizar",
        )

    result = products_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID '{id}' no encontrado",
        )

    updated_product = products_collection.find_one({"_id": obj_id})
    return serialize_doc(updated_product)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar un producto",
    description="Elimina un producto existente por su ID.",
)
def delete_product(id: str):
    obj_id = validate_object_id(id)
    result = products_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID '{id}' no encontrado",
        )
    return {"message": f"Producto con ID '{id}' eliminado correctamente"}
