from datetime import datetime, timezone
import json
import math

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.database.database import client, orders_collection, products_collection
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
RESTOCKABLE_ORDER_STATUSES = {
    order_status
    for order_status, next_statuses in ORDER_STATUS_TRANSITIONS.items()
    if "cancelado" in next_statuses
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


def _restore_order_stock(order: dict, session) -> None:
    """Devuelve al inventario las unidades de un pedido que aún no fue enviado."""
    # Los pedidos previos a la reserva de inventario no deben inflar existencias
    # cuando se cancelen o eliminen después del despliegue.
    if not order.get("stock_reserved"):
        return
    for item in order.get("items", []):
        if not isinstance(item, dict):
            continue
        product_id_value = str(item.get("product_id") or "")
        try:
            product_id = validate_object_id(product_id_value)
            quantity = int(item.get("quantity") or 0)
        except (HTTPException, TypeError, ValueError):
            # Los pedidos antiguos pueden no tener líneas con IDs restaurables.
            continue
        if quantity > 0:
            products_collection.update_one(
                {"_id": product_id},
                {"$inc": {"stock": quantity}},
                session=session,
            )


def _cancel_order_atomically(order_filter: dict, allowed_statuses: set[str]):
    """Cambia el estado y restaura existencias dentro de una transacción."""
    def cancel(session):
        order = orders_collection.find_one(order_filter, session=session)
        if not order:
            raise HTTPException(status_code=404, detail="No se encontró ese pedido.")

        current_status = _normalized_status(order.get("status", "pendiente"))
        if current_status not in allowed_statuses:
            raise HTTPException(
                status_code=409,
                detail="El pedido ya avanzó y no se puede cancelar en este estado.",
            )

        now = datetime.now(timezone.utc).isoformat()
        status_filter = order.get("status")
        if "status" not in order:
            status_filter = {"$exists": False}
        result = orders_collection.update_one(
            {**order_filter, "status": status_filter},
            {
                "$set": {"status": "cancelado", "cancelled_at": now},
                "$push": {"status_history": {"status": "cancelado", "at": now}},
            },
            session=session,
        )
        if result.modified_count == 0:
            raise HTTPException(
                status_code=409,
                detail="El estado del pedido cambió. Actualiza la página.",
            )

        _restore_order_stock(order, session)
        return serialize_doc(orders_collection.find_one(order_filter, session=session))

    with client.start_session() as session:
        return session.with_transaction(cancel)


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
    quantities_by_product = {}
    for requested in order.items:
        quantities_by_product[requested.product_id] = quantities_by_product.get(requested.product_id, 0) + requested.quantity
    checkout_fingerprint = json.dumps(
        sorted(quantities_by_product.items()), separators=(",", ":")
    )

    if order.checkout_key:
        orders_collection.create_index(
            [("user_id", 1), ("checkout_key", 1)],
            unique=True,
            partialFilterExpression={"checkout_key": {"$type": "string"}},
            name="user_checkout_key_unique",
        )

    def create(session):
        if order.checkout_key:
            existing = orders_collection.find_one(
                {"user_id": str(current_user["_id"]), "checkout_key": order.checkout_key},
                session=session,
            )
            if existing:
                if existing.get("checkout_fingerprint") != checkout_fingerprint:
                    raise HTTPException(status_code=409, detail="El contenido del pedido cambió. Actualiza el carrito antes de confirmar.")
                return serialize_doc(existing)

        items = []
        total = 0.0
        total_quantity = 0
        for product_id_value, quantity in quantities_by_product.items():
            if quantity > 99:
                raise HTTPException(status_code=422, detail="La cantidad máxima por producto es 99.")
            product_id = validate_object_id(product_id_value)

            # El filtro y el decremento ocurren en una sola operación atómica:
            # dos compras simultáneas no pueden consumir las mismas unidades.
            product = products_collection.find_one_and_update(
                {"_id": product_id, "stock": {"$gte": quantity}},
                {"$inc": {"stock": -quantity}},
                return_document=ReturnDocument.BEFORE,
                session=session,
            )
            if not product:
                current_product = products_collection.find_one(
                    {"_id": product_id}, {"name": 1, "stock": 1}, session=session
                )
                if not current_product:
                    raise HTTPException(status_code=404, detail="Uno de los productos ya no está disponible.")
                available_stock = max(0, int(current_product.get("stock") or 0))
                raise HTTPException(
                    status_code=409,
                    detail=f"Solo quedan {available_stock} unidad(es) de {current_product.get('name', 'este producto')}.",
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
            "stock_reserved": True,
            "checkout_key": order.checkout_key,
            "checkout_fingerprint": checkout_fingerprint if order.checkout_key else None,
            "created_at": created_at,
            "status_history": [{"status": "pendiente", "at": created_at}],
        }
        result = orders_collection.insert_one(order_doc, session=session)
        return serialize_doc(orders_collection.find_one({"_id": result.inserted_id}, session=session))

    # El descuento y la creación del pedido se confirman juntos o se revierten juntos.
    try:
        with client.start_session() as session:
            return session.with_transaction(create)
    except DuplicateKeyError:
        # A retry may race with the first request. Return its committed order
        # instead of decrementing inventory or creating a duplicate.
        existing = orders_collection.find_one(
            {"user_id": str(current_user["_id"]), "checkout_key": order.checkout_key}
        ) if order.checkout_key else None
        if existing and existing.get("checkout_fingerprint") == checkout_fingerprint:
            return serialize_doc(existing)
        raise HTTPException(status_code=409, detail="No se pudo confirmar el pedido duplicado. Actualiza el carrito e inténtalo de nuevo.")


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
    return _cancel_order_atomically(owner_query, {"pendiente"})


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

    requested_status = update_data.get("status")
    if requested_status == "cancelado":
        current_order = orders_collection.find_one({"_id": obj_id})
        if not current_order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado.")
        if _normalized_status(current_order.get("status", "pendiente")) == "cancelado":
            return serialize_doc(current_order)
        return _cancel_order_atomically({"_id": obj_id}, RESTOCKABLE_ORDER_STATUSES)

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

    def delete(session):
        order = orders_collection.find_one({"_id": obj_id}, session=session)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado.")

        current_status = _normalized_status(order.get("status", "pendiente"))
        if current_status in RESTOCKABLE_ORDER_STATUSES:
            _restore_order_stock(order, session)

        status_filter = order.get("status")
        if "status" not in order:
            status_filter = {"$exists": False}
        result = orders_collection.delete_one(
            {"_id": obj_id, "status": status_filter}, session=session
        )
        if result.deleted_count == 0:
            raise HTTPException(status_code=409, detail="El pedido cambió. Actualiza la página e inténtalo de nuevo.")
        return {"message": "Pedido eliminado correctamente"}

    with client.start_session() as session:
        return session.with_transaction(delete)
