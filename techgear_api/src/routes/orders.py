from fastapi import APIRouter, HTTPException, status

from src.database.database import orders_collection
from src.models.order import OrderModel, OrderUpdateModel
from src.utils.mongo import serialize_doc, validate_object_id

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo pedido",
    description="Registra un pedido en el sistema validando campos como email del cliente, cantidad y total.",
)
def create_order(order: OrderModel):
    order_dict = order.model_dump()
    result = orders_collection.insert_one(order_dict)
    created_order = orders_collection.find_one({"_id": result.inserted_id})
    return serialize_doc(created_order)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Listar todos los pedidos",
    description="Devuelve la lista completa de pedidos registrados.",
)
def list_orders():
    orders = list(orders_collection.find())
    return [serialize_doc(o) for o in orders]


@router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Obtener un pedido por ID",
    description="Busca un pedido por su identificador único de MongoDB.",
)
def get_order(id: str):
    obj_id = validate_object_id(id)
    order = orders_collection.find_one({"_id": obj_id})
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido con ID '{id}' no encontrado",
        )
    return serialize_doc(order)


@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Actualizar un pedido",
    description="Actualiza el estado u otros datos de un pedido existente.",
)
def update_order(id: str, order_data: OrderUpdateModel):
    obj_id = validate_object_id(id)
    update_data = order_data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar al menos un campo para actualizar",
        )

    result = orders_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido con ID '{id}' no encontrado",
        )

    updated_order = orders_collection.find_one({"_id": obj_id})
    return serialize_doc(updated_order)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar un pedido",
    description="Elimina un pedido existente por su ID.",
)
def delete_order(id: str):
    obj_id = validate_object_id(id)
    result = orders_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido con ID '{id}' no encontrado",
        )
    return {"message": f"Pedido con ID '{id}' eliminado correctamente"}
