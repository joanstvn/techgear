from datetime import datetime, timezone
import math

from fastapi import APIRouter, Depends, HTTPException, status

from src.database.database import orders_collection, products_collection
from src.models.order import CartOrderModel, OrderModel, OrderUpdateModel
from src.utils.mongo import serialize_doc, validate_object_id
from src.utils.security import get_current_user, require_admin

router = APIRouter()

ORDER_STATUS_TRANSITIONS = {
    "pendiente": {"confirmado", "cancelado"},
    "confirmado": {"en_preparacion", "cancelado"},
    "en_preparacion": {"enviado", "cancelado"},
    "enviado": {"entregado"},
    "entregado": set(),
    "cancelado": set(),
}


def _normalized_status(value: str) -> str:
    status_value = str(value or "pendiente").strip().lower().replace(" ", "_")
    return {
        "en_preparación": "en_preparacion",
        "preparando": "en_preparacion",
        "completado": "entregado",
        "completada": "entregado",
        "completed": "entregado",
        "cancelled": "cancelado",
        "canceled": "cancelado",
    }.get(status_value, status_value)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo pedido",
    description="Registra un pedido en el sistema validando campos como email del cliente, cantidad y total.",
)
def create_order(order: OrderModel, current_user: dict = Depends(get_current_user)):
    return create_cart_order(
        CartOrderModel(items=[{"product_id": order.product_id, "quantity": order.quantity}]),
        current_user,
    )


@router.post(
    "/cart",
    status_code=status.HTTP_201_CREATED,
    summary="Crear un pedido desde el carrito",
)
def create_cart_order(
    order: CartOrderModel,
    current_user: dict = Depends(get_current_user),
):
    """Crea un pedido autenticado calculando nombres y precios desde MongoDB."""
    items = []
    total = 0.0
    total_quantity = 0
    quantities_by_product = {}
    for requested in order.items:
        quantities_by_product[requested.product_id] = quantities_by_product.get(requested.product_id, 0) + requested.quantity
    for product_id_value, quantity in quantities_by_product.items():
        if quantity > 99:
            raise HTTPException(status_code=422, detail="La cantidad máxima por producto es 99.")
        product_id = validate_object_id(product_id_value)
        product = products_collection.find_one({"_id": product_id})
        if not product:
            raise HTTPException(status_code=404, detail="Uno de los productos ya no está disponible.")
        stock = max(0, int(product.get("stock") or 0))
        if quantity > stock:
            raise HTTPException(
                status_code=409,
                detail=f"Solo quedan {stock} unidad(es) de {product.get('name', 'este producto')}.",
            )
        unit_price = float(product.get("price") or 0)
        if not math.isfinite(unit_price) or unit_price <= 0:
            raise HTTPException(status_code=409, detail="Uno de los productos no tiene un precio válido.")
        subtotal = round(unit_price * quantity, 2)
        items.append({
            "product_id": str(product_id),
            "name": product.get("name", "Producto"),
            "image": product.get("image") or product.get("image_url") or "",
            "quantity": quantity,
            "unit_price": unit_price,
            "subtotal": subtotal,
        })
        total += subtotal
        total_quantity += quantity

    created_at = datetime.now(timezone.utc).isoformat()
    order_doc = {
        "customer_name": current_user.get("full_name") or current_user.get("username", "Cliente"),
        "customer_email": current_user.get("email", ""),
        "user_id": str(current_user["_id"]),
        "items": items,
        # Campos legados para que las integraciones existentes sigan leyendo pedidos.
        "product": ", ".join(item["name"] for item in items),
        "quantity": total_quantity,
        "total_price": round(total, 2),
        "status": "pendiente",
        "created_at": created_at,
        "status_history": [{"status": "pendiente", "at": created_at}],
    }
    result = orders_collection.insert_one(order_doc)
    return serialize_doc(orders_collection.find_one({"_id": result.inserted_id}))


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Listar todos los pedidos",
    description="Devuelve la lista completa de pedidos registrados.",
)
def list_orders(current_user: dict = Depends(require_admin)):
    orders = list(orders_collection.find().sort("created_at", -1))
    return [serialize_doc(o) for o in orders]


@router.get(
    "/mine",
    status_code=status.HTTP_200_OK,
    summary="Listar los pedidos del usuario autenticado",
)
def list_my_orders(current_user: dict = Depends(get_current_user)):
    orders = list(
        orders_collection.find({"user_id": str(current_user["_id"])}).sort("created_at", -1)
    )
    for order in orders:
        order.setdefault("items", [])
        order.setdefault("created_at", "")
        for item in order["items"]:
            if isinstance(item, dict):
                item.setdefault("image", "")
    return [serialize_doc(order) for order in orders]


@router.post(
    "/{id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancelar un pedido propio pendiente",
)
def cancel_my_order(id: str, current_user: dict = Depends(get_current_user)):
    obj_id = validate_object_id(id)
    owner_query = {"_id": obj_id, "user_id": str(current_user["_id"])}
    order = orders_collection.find_one(owner_query)
    if not order:
        raise HTTPException(status_code=404, detail="No se encontró ese pedido en tu cuenta.")
    if str(order.get("status", "")).lower() != "pendiente":
        raise HTTPException(status_code=409, detail="Solo puedes cancelar pedidos pendientes.")

    result = orders_collection.update_one(
        {**owner_query, "status": order.get("status")},
        {
            "$set": {"status": "cancelado", "cancelled_at": datetime.now(timezone.utc).isoformat()},
            "$push": {"status_history": {"status": "cancelado", "at": datetime.now(timezone.utc).isoformat()}},
        },
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=409, detail="El estado del pedido cambió. Actualiza la página.")
    return serialize_doc(orders_collection.find_one(owner_query))


@router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Obtener un pedido por ID",
    description="Busca un pedido por su identificador único de MongoDB.",
)
def get_order(id: str, current_user: dict = Depends(require_admin)):
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
def update_order(
    id: str,
    order_data: OrderUpdateModel,
    current_user: dict = Depends(require_admin),
):
    obj_id = validate_object_id(id)
    update_data = order_data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar al menos un campo para actualizar",
        )

    current_order = orders_collection.find_one({"_id": obj_id})
    if not current_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pedido con ID '{id}' no encontrado")

    current_status = _normalized_status(current_order.get("status", "pendiente"))
    requested_status = update_data.get("status")
    update_filter = {"_id": obj_id}
    mongo_update = {"$set": update_data}
    if requested_status and requested_status != current_status:
        if requested_status not in ORDER_STATUS_TRANSITIONS.get(current_status, set()):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ese cambio de estado no está permitido. Sigue el flujo del pedido.",
            )
        now = datetime.now(timezone.utc).isoformat()
        if "status" in current_order:
            update_filter["status"] = current_order["status"]
        else:
            update_filter["status"] = {"$exists": False}
        update_data["status_updated_at"] = now
        mongo_update["$push"] = {
            "status_history": {"status": requested_status, "at": now}
        }

    result = orders_collection.update_one(
        update_filter,
        mongo_update,
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El pedido cambió mientras lo actualizabas. Recarga la página e inténtalo de nuevo.",
        )

    updated_order = orders_collection.find_one({"_id": obj_id})
    return serialize_doc(updated_order)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar un pedido",
    description="Elimina un pedido existente por su ID.",
)
def delete_order(id: str, current_user: dict = Depends(require_admin)):
    obj_id = validate_object_id(id)
    result = orders_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido con ID '{id}' no encontrado",
        )
    return {"message": f"Pedido con ID '{id}' eliminado correctamente"}
