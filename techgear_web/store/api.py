"""Cliente HTTP para comunicar el frontend Django con la API de TechGear."""

from typing import Any, Optional

import requests
from django.conf import settings


class ApiError(Exception):
    """Error producido al consumir la API de TechGear."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _url(path: str) -> str:
    return f"{settings.API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _extract_detail(response: requests.Response) -> str:
    """Obtiene un mensaje legible del cuerpo de error devuelto por FastAPI."""
    try:
        body = response.json()
    except ValueError:
        return "La API devolvió una respuesta inesperada."

    detail = body.get("detail") if isinstance(body, dict) else None

    if isinstance(detail, list):
        # Errores de validación de Pydantic
        messages = []
        for item in detail:
            if isinstance(item, dict):
                field = ".".join(str(part) for part in item.get("loc", [])[1:])
                messages.append(f"{field}: {item.get('msg', 'valor inválido')}".strip(": "))
        return ". ".join(messages) or "Los datos enviados no son válidos."

    if isinstance(detail, str):
        return detail

    return "Ocurrió un error al comunicarse con la API."


def _request(
    method: str,
    path: str,
    **kwargs: Any,
) -> Any:
    headers = kwargs.pop("headers", {})

    try:
        response = requests.request(
            method,
            _url(path),
            headers=headers,
            timeout=settings.API_TIMEOUT,
            **kwargs,
        )
    except requests.RequestException:
        raise ApiError(
            "No se pudo conectar con la API de TechGear. "
            "Verifica que el backend esté en ejecución."
        )

    if response.status_code >= 400:
        raise ApiError(_extract_detail(response), response.status_code)

    if not response.content:
        return None

    try:
        return response.json()
    except ValueError:
        return None


def _admin_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


# Autenticación


def login(username: str, password: str) -> dict:
    return _request(
        "POST",
        "/auth/login",
        json={"username": username, "password": password},
    )


def register(data: dict) -> dict:
    return _request("POST", "/auth/register", json=data)


# Catálogo de productos


def list_products() -> list:
    return _request("GET", "/products/") or []


def get_product(product_id: str) -> dict:
    return _request("GET", f"/products/{product_id}")


def create_product(data: dict, token: str = "") -> dict:
    return _request("POST", "/products/", json=data, headers=_admin_headers(token))


def update_product(product_id: str, data: dict, token: str = "") -> dict:
    return _request("PUT", f"/products/{product_id}", json=data, headers=_admin_headers(token))


def delete_product(product_id: str, token: str = "") -> dict:
    return _request("DELETE", f"/products/{product_id}", headers=_admin_headers(token))


# Pedidos


def create_order(data: dict) -> dict:
    return _request("POST", "/orders/", json=data)


def create_cart_order(data: dict, token: str) -> dict:
    return _request(
        "POST", "/orders/cart", json=data, headers=_admin_headers(token)
    )


def list_orders(token: str) -> list:
    return _request("GET", "/orders/", headers=_admin_headers(token)) or []


def update_order_status(order_id: str, status: str, token: str) -> dict:
    return _request(
        "PUT",
        f"/orders/{order_id}",
        json={"status": status},
        headers=_admin_headers(token),
    )


def list_my_orders(token: str) -> list:
    return _request("GET", "/orders/mine", headers=_admin_headers(token)) or []


def cancel_my_order(order_id: str, token: str) -> dict:
    return _request(
        "POST", f"/orders/{order_id}/cancel", headers=_admin_headers(token)
    )


# Usuarios (requiere token de administrador)


def list_users(token: str) -> list:
    return _request("GET", "/users/", headers=_admin_headers(token)) or []


def create_user(data: dict, token: str) -> dict:
    return _request("POST", "/users/", json=data, headers=_admin_headers(token))


def update_user(user_id: str, data: dict, token: str) -> dict:
    return _request("PUT", f"/users/{user_id}", json=data, headers=_admin_headers(token))


def delete_user(user_id: str, token: str) -> dict:
    return _request("DELETE", f"/users/{user_id}", headers=_admin_headers(token))
