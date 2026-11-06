from django.contrib import messages
from django.conf import settings
from django.core.validators import MaxValueValidator
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from functools import wraps
from urllib.parse import urlencode
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from django.views.decorators.http import require_POST
import requests

from store import api
from store.forms import (
    AdminProductForm,
    AdminUserForm,
    LoginForm,
    OrderForm,
    PasswordResetRequestForm,
    RegisterForm,
)

ORDER_STATUS_LABELS = {
    "pendiente": "Pendiente",
    "confirmado": "Confirmado",
    "en_preparacion": "En preparación",
    "enviado": "Enviado",
    "entregado": "Entregado",
    "cancelado": "Cancelado",
}
ORDER_STATUS_NEXT = {
    "pendiente": ("confirmado", "cancelado"),
    "confirmado": ("en_preparacion", "cancelado"),
    "en_preparacion": ("enviado", "cancelado"),
    "enviado": ("entregado",),
    "entregado": (),
    "cancelado": (),
}
ORDER_STATUS_FLOW = ("pendiente", "confirmado", "en_preparacion", "enviado", "entregado")
ORDER_STATUS_DESCRIPTIONS = {
    "pendiente": "Tu solicitud fue recibida y está pendiente de revisión.",
    "confirmado": "El equipo confirmó tu pedido y coordinará contigo el pago y la entrega.",
    "en_preparacion": "Estamos preparando los productos de tu pedido.",
    "enviado": "Tu pedido fue enviado.",
    "entregado": "Tu pedido figura como entregado.",
    "cancelado": "Este pedido fue cancelado.",
}


def _safe_next_url(request, candidate):
    candidate = (candidate or '').strip()
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return ''


def _order_status_key(value):
    key = str(value or "pendiente").strip().lower().replace(" ", "_")
    return {
        "en_preparación": "en_preparacion",
        "completado": "entregado",
        "completada": "entregado",
        "completed": "entregado",
        "cancelled": "cancelado",
        "canceled": "cancelado",
    }.get(key, key)


def _decorate_order_status(order, include_options=False):
    order = dict(order)
    key = _order_status_key(order.get("status"))
    order["status_key"] = key
    order["status_label"] = ORDER_STATUS_LABELS.get(key, str(order.get("status") or "Pendiente").capitalize())
    order["status_description"] = ORDER_STATUS_DESCRIPTIONS.get(key, "Consulta aquí las novedades de tu pedido.")
    order["status_progress"] = round((ORDER_STATUS_FLOW.index(key) / (len(ORDER_STATUS_FLOW) - 1)) * 100) if key in ORDER_STATUS_FLOW else 0
    if include_options:
        option_keys = (key,) + ORDER_STATUS_NEXT.get(key, ())
        order["status_options"] = [
            {"value": option, "label": ORDER_STATUS_LABELS[option], "selected": option == key}
            for option in option_keys
        ]
        order["can_update_status"] = bool(ORDER_STATUS_NEXT.get(key, ()))
    return order


def _productos_y_categorias():
    """Obtiene productos y categorías del catálogo, tolerando fallos de la API."""
    try:
        products = api.list_products()
    except api.ApiError:
        return [], [], True
    categories = sorted(
        {product.get("category", "") for product in products if product.get("category")}
    )
    return products, categories, False


# Landing


def home(request):
    products, categories, catalog_unavailable = _productos_y_categorias()
    en_stock = sum(1 for product in products if _stock_value(product) > 0)

    return render(
        request,
        "landing.html",
        {
            "featured_products": products[:3],
            "total_products": len(products),
            "total_categories": len(categories),
            "in_stock": en_stock,
            "catalog_unavailable": catalog_unavailable,
        },
    )


# Catálogo público


def catalog(request):
    catalog_unavailable = False
    try:
        products = api.list_products()
    except api.ApiError:
        products = []
        catalog_unavailable = True
    for product in products:
        product["in_stock"] = _stock_value(product) > 0

    query = request.GET.get("q", "").strip()
    category = request.GET.get("categoria", "").strip()

    if query:
        needle = query.lower()
        products = [
            product
            for product in products
            if needle in str(product.get("name", "")).lower()
            or needle in str(product.get("description", "")).lower()
            or needle in str(product.get("category", "")).lower()
        ]

    categories = sorted({product.get("category", "") for product in products if product.get("category")})

    if category:
        products = [product for product in products if product.get("category") == category]

    return render(
        request,
        "catalog.html",
        {
            "products": products,
            "categories": categories,
            "query": query,
            "selected_category": category,
            "catalog_unavailable": catalog_unavailable,
        },
    )


def product_detail(request, id: str):
    try:
        product = api.get_product(id)
    except api.ApiError as error:
        messages.error(request, error.message)
        return redirect("store:catalog")

    form = _order_form_for_product(request.POST or None, product)
    return render(
        request,
        "product_detail.html",
        {"product": product, "form": form, "cart_count": _cart_count(request)},
    )


def _cart_count(request):
    cart = request.session.get("cart") or {}
    if not isinstance(cart, dict):
        request.session["cart"] = {}
        return 0
    total = 0
    for quantity in cart.values():
        try:
            total += max(0, min(99, int(quantity)))
        except (TypeError, ValueError):
            continue
    return total


def _stock_value(product):
    try:
        return max(0, int(product.get("stock") or 0))
    except (TypeError, ValueError, AttributeError):
        return 0


def cart_context(request):
    return {"cart_count": _cart_count(request)}


def _cart_products(request):
    cart = request.session.get("cart") or {}
    if not isinstance(cart, dict):
        request.session["cart"] = {}
        return [], 0, False, False
    if not cart:
        return [], 0, False, False
    try:
        products = api.list_products()
    except api.ApiError:
        return [], 0, True, False
    by_id = {}
    for product in products:
        product.setdefault("image", product.get("image_url") or "")
        by_id[str(product.get("id"))] = product
    rows = []
    cleaned_cart = {}
    total = 0.0
    stock_issue = False
    removed_count = 0
    for product_id, raw_quantity in cart.items():
        product = by_id.get(str(product_id))
        if not product:
            removed_count += 1
            continue
        try:
            raw_value = int(raw_quantity)
            quantity = max(1, min(99, raw_value))
            stock = _stock_value(product)
        except (TypeError, ValueError):
            removed_count += 1
            continue
        if stock < 1 or quantity > stock:
            stock_issue = True
        if raw_value > 99:
            messages.warning(request, "La cantidad máxima por producto es 99; actualizamos el carrito.")
        try:
            price = max(0.0, float(product.get("price") or 0))
        except (TypeError, ValueError):
            price = 0.0
            stock_issue = True
        subtotal = round(price * quantity, 2) if stock > 0 and quantity <= stock else 0
        cleaned_cart[str(product_id)] = quantity
        rows.append({"product": product, "quantity": quantity, "subtotal": subtotal,
                     "available": stock > 0 and quantity <= stock, "stock": stock})
        total += subtotal
    if cleaned_cart != cart:
        request.session["cart"] = cleaned_cart
        request.session.pop("cart_checkout_key", None)
    if removed_count:
        messages.warning(request, "Quitamos del carrito los productos que ya no están disponibles.")
    if stock_issue:
        messages.warning(request, "Hay productos sin stock suficiente. Ajusta o quita esas cantidades antes de confirmar.")
    return rows, round(total, 2), False, stock_issue


def cart_view(request):
    cart = request.session.get("cart") or {}
    if isinstance(cart, dict) and cart and not request.session.get("cart_checkout_key"):
        request.session["cart_checkout_key"] = uuid4().hex
    rows, total, cart_unavailable, stock_issue = _cart_products(request)
    return render(request, "cart.html", {
        "cart_rows": rows,
        "cart_total": total,
        "cart_count": _cart_count(request),
        "cart_unavailable": cart_unavailable,
        "stock_issue": stock_issue,
    })


@require_POST
def cart_add(request, id: str):
    try:
        product = api.get_product(id)
    except api.ApiError as error:
        if error.status_code == 404:
            messages.error(request, "Este producto ya no está disponible.")
        else:
            messages.error(request, error.message)
        return redirect("store:catalog")
    try:
        stock = max(0, int(product.get("stock") or 0))
        quantity = max(1, int(request.POST.get("quantity", "1")))
    except (TypeError, ValueError):
        stock, quantity = 0, 1
    if stock < 1:
        messages.error(request, "Este producto no tiene unidades disponibles.")
        return redirect("store:product_detail", id=id)
    cart = request.session.get("cart") or {}
    if not isinstance(cart, dict):
        cart = {}
    if id not in cart and len(cart) >= 30:
        messages.error(request, "El carrito admite hasta 30 productos distintos.")
        return redirect("store:product_detail", id=id)
    try:
        current_quantity = max(0, min(99, int(cart.get(id, 0))))
    except (TypeError, ValueError):
        current_quantity = 0
    requested_total = current_quantity + quantity
    allowed_quantity = min(stock, 99)
    cart[id] = min(allowed_quantity, requested_total)
    request.session["cart"] = cart
    request.session.pop("cart_checkout_key", None)
    product_name = product.get("name", "Producto")
    if requested_total > allowed_quantity:
        messages.warning(request, f"La cantidad se ajustó al máximo disponible ({allowed_quantity}) para {product_name}.")
    if request.session.get("user") and request.session.get("token"):
        messages.success(request, f"{product_name} se añadió al carrito.")
    return redirect("store:cart")


@require_POST
def cart_update(request, id: str):
    cart = request.session.get("cart") or {}
    if not isinstance(cart, dict):
        request.session["cart"] = {}
        return redirect("store:cart")
    if id not in cart:
        return redirect("store:cart")
    try:
        quantity = int(request.POST.get("quantity", "1"))
    except (ValueError, TypeError):
        messages.error(request, "Escribe una cantidad válida.")
        return redirect("store:cart")
    if quantity < 1:
        cart.pop(id, None)
        request.session["cart"] = cart
        request.session.pop("cart_checkout_key", None)
        return redirect("store:cart")
    try:
        product = api.get_product(id)
        stock = _stock_value(product)
    except api.ApiError as error:
        if error.status_code == 404:
            cart.pop(id, None)
            request.session["cart"] = cart
            messages.warning(request, "El producto ya no está disponible y se quitó del carrito.")
            return redirect("store:cart")
        messages.error(request, error.message)
        return redirect("store:cart")
    except (ValueError, TypeError):
        messages.error(request, "No se pudo actualizar la cantidad.")
        return redirect("store:cart")
    if stock < 1:
        cart[id] = quantity
        messages.error(request, "El producto está agotado. Quítalo del carrito para continuar.")
    else:
        cart[id] = min(quantity, stock, 99)
        if quantity > min(stock, 99):
            messages.warning(request, f"La cantidad se ajustó al máximo disponible ({min(stock, 99)}).")
    request.session["cart"] = cart
    request.session.pop("cart_checkout_key", None)
    return redirect("store:cart")


@require_POST
def cart_remove(request, id: str):
    cart = request.session.get("cart") or {}
    if not isinstance(cart, dict):
        cart = {}
    else:
        cart.pop(id, None)
    request.session["cart"] = cart
    request.session.pop("cart_checkout_key", None)
    return redirect("store:cart")


@require_POST
def cart_checkout(request):
    user = request.session.get("user") or {}
    token = request.session.get("token", "")
    if not user or not token:
        next_url = urlencode({"next": reverse("store:cart")})
        return redirect(f"{reverse('store:login')}?{next_url}")
    cart = request.session.get("cart") or {}
    if not isinstance(cart, dict) or not cart:
        request.session["cart"] = {}
        messages.error(request, "Tu carrito está vacío.")
        return redirect("store:cart")
    try:
        items = [{"product_id": str(product_id), "quantity": max(1, min(99, int(quantity)))}
                 for product_id, quantity in cart.items()]
    except (TypeError, ValueError):
        messages.error(request, "El carrito contiene una cantidad inválida. Revísalo antes de continuar.")
        return redirect("store:cart")
    # Recheck current stock before sending the order. The API repeats this check
    # atomically while decrementing inventory, closing the race between requests.
    try:
        current_products = {str(item.get("id")): item for item in api.list_products()}
    except api.ApiError as error:
        messages.error(request, error.message)
        return redirect("store:cart")
    stale_items = [item for item in items if item["product_id"] not in current_products]
    if stale_items:
        for item in stale_items:
            cart.pop(item["product_id"], None)
        request.session["cart"] = cart
        request.session.pop("cart_checkout_key", None)
        messages.warning(request, "Quitamos del carrito productos que ya no están disponibles. Revísalo antes de confirmar.")
        return redirect("store:cart")
    unavailable = []
    for item in items:
        current_stock = _stock_value(current_products[item["product_id"]])
        if current_stock < item["quantity"]:
            unavailable.append((item["product_id"], current_stock))
    if unavailable:
        for product_id, current_stock in unavailable:
            if current_stock > 0:
                cart[product_id] = current_stock
        request.session["cart"] = cart
        request.session.pop("cart_checkout_key", None)
        messages.error(request, "El stock cambió mientras revisabas el carrito. Ajustamos las cantidades disponibles; revísalas y vuelve a confirmar.")
        return redirect("store:cart")
    checkout_key = request.session.get("cart_checkout_key") or uuid4().hex
    request.session["cart_checkout_key"] = checkout_key
    try:
        api.create_cart_order({"items": items, "checkout_key": checkout_key}, token)
    except api.ApiError as error:
        messages.error(request, error.message)
        return redirect("store:cart")
    request.session["cart"] = {}
    request.session.pop("cart_checkout_key", None)
    messages.success(request, "Recibimos tu pedido. Puedes seguir su estado en Mis pedidos; coordinaremos contigo el pago y la entrega.")
    return redirect("store:my_orders")


def my_orders(request):
    if not request.session.get("user") or not request.session.get("token"):
        next_url = urlencode({"next": reverse("store:my_orders")})
        return redirect(f"{reverse('store:login')}?{next_url}")
    orders_unavailable = False
    try:
        orders = api.list_my_orders(request.session["token"])
    except api.ApiError:
        orders = []
        orders_unavailable = True
    orders = [_decorate_order_status(order) for order in orders]
    return render(request, "my_orders.html", {
        "orders": orders,
        "orders_unavailable": orders_unavailable,
    })


@require_POST
def cancel_my_order(request, id: str):
    if not request.session.get("user") or not request.session.get("token"):
        next_url = urlencode({"next": reverse("store:my_orders")})
        return redirect(f"{reverse('store:login')}?{next_url}")
    try:
        api.cancel_my_order(id, request.session["token"])
        messages.success(request, "El pedido se canceló correctamente.")
    except api.ApiError as error:
        messages.error(request, error.message)
    return redirect("store:my_orders")


@require_POST
def create_order(request, id: str):
    # Ruta antigua: convierte la intención de compra en una acción de carrito,
    # nunca registra un pedido sin pasar por la revisión y confirmación del carrito.
    return cart_add(request, id)


def _order_form_for_product(data, product, initial=None):
    form = OrderForm(data, initial=initial)
    try:
        stock = max(0, int(product.get("stock") or 0))
    except (TypeError, ValueError):
        stock = 0
    quantity_field = form.fields["quantity"]
    quantity_field.widget.attrs["max"] = stock
    quantity_field.validators.append(MaxValueValidator(stock))
    return form


def admin_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        user = request.session.get("user") or {}
        if not user:
            return redirect(f"{reverse('store:login')}?next={reverse('store:admin_dashboard')}")
        if str(user.get("role", "")).lower() not in {"admin", "administrador"}:
            messages.error(request, "Esta sección está disponible solo para administradores.")
            return redirect("store:home")
        return view(request, *args, **kwargs)
    return wrapped


@admin_required
def admin_dashboard(request):
    api_error = False
    api_auth_error = False
    token = request.session.get("token", "")
    fetchers = {
        "products": api.list_products,
        "users": lambda: api.list_users(token),
        "orders": lambda: api.list_orders(token),
    }
    results = {"products": [], "users": [], "orders": []}
    # A sleeping API should cost one short wait, not one wait per admin tab.
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {name: executor.submit(fetch) for name, fetch in fetchers.items()}
        for name, future in futures.items():
            try:
                results[name] = future.result()
            except api.ApiError as error:
                api_error = True
                if error.status_code in {401, 403}:
                    api_auth_error = True
    products = results["products"]
    users = results["users"]
    orders = results["orders"]
    orders = [_decorate_order_status(order, include_options=True) for order in orders]
    return render(request, "admin/dashboard.html", {
        "products": products,
        "users": users,
        "orders": orders,
        "total_products": len(products),
        "total_users": len(users),
        "total_orders": len(orders),
        "total_stock": sum(_stock_value(product) for product in products),
        "total_categories": len({product.get("category") for product in products if product.get("category")}),
        "api_error": api_error,
        "api_auth_error": api_auth_error,
        "today": timezone.localdate(),
        "product_form": AdminProductForm(),
        "user_form": AdminUserForm(),
    })


def _admin_section_redirect(section: str):
    return redirect(f"{reverse('store:admin_dashboard')}?section={section}")


@admin_required
@require_POST
def admin_update_order_status(request, id: str):
    requested_status = request.POST.get("status", "")
    if requested_status not in ORDER_STATUS_LABELS:
        messages.error(request, "Selecciona un estado válido para el pedido.")
        return redirect(f"{reverse('store:admin_dashboard')}?section=orders")
    try:
        api.update_order_status(id, requested_status, request.session.get("token", ""))
        messages.success(request, "El estado del pedido se actualizó correctamente.")
    except api.ApiError as error:
        messages.error(request, error.message)
    return redirect(f"{reverse('store:admin_dashboard')}?section=orders")


def _upload_product_image(uploaded_file):
    cloud_name = settings.CLOUDINARY_CLOUD_NAME
    api_key = settings.CLOUDINARY_API_KEY
    api_secret = settings.CLOUDINARY_API_SECRET
    if not all((cloud_name, api_key, api_secret)):
        raise api.ApiError(
            "La carga de archivos requiere configurar Cloudinary en las variables de entorno."
        )

    try:
        response = requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
            auth=(api_key, api_secret),
            data={"folder": "techgear/products"},
            files={
                "file": (
                    uploaded_file.name,
                    uploaded_file.file,
                    uploaded_file.content_type,
                )
            },
            timeout=(5, 45),
        )
        response.raise_for_status()
        image_url = response.json().get("secure_url")
    except (requests.RequestException, ValueError):
        raise api.ApiError("No se pudo subir la imagen. Revisa el archivo e inténtalo de nuevo.")

    if not image_url:
        raise api.ApiError("El servicio de imágenes no devolvió una URL válida.")
    return image_url


def _product_data(form):
    data = form.cleaned_data.copy()
    uploaded_file = data.pop("image_file", None)
    image_url = data.pop("image_url", "")
    data["image"] = _upload_product_image(uploaded_file) if uploaded_file else image_url
    data["price"] = float(data["price"])
    return data


@admin_required
@require_POST
def admin_create_product(request):
    form = AdminProductForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            data = _product_data(form)
            api.create_product(data, request.session.get("token", ""))
            messages.success(request, "El producto se agregó al catálogo.")
        except api.ApiError as error:
            messages.error(request, error.message)
    else:
        messages.error(request, "Revisa los datos del producto e inténtalo de nuevo.")
    return _admin_section_redirect("products")


@admin_required
@require_POST
def admin_update_product(request, id):
    form = AdminProductForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            data = _product_data(form)
            api.update_product(id, data, request.session.get("token", ""))
            messages.success(request, "Los cambios del producto se guardaron.")
        except api.ApiError as error:
            messages.error(request, error.message)
    else:
        messages.error(request, "Revisa los datos del producto e inténtalo de nuevo.")
    return _admin_section_redirect("products")


@admin_required
@require_POST
def admin_delete_product(request, id):
    try:
        api.delete_product(id, request.session.get("token", ""))
        messages.success(request, "El producto se eliminó del catálogo.")
    except api.ApiError as error:
        messages.error(request, error.message)
    return _admin_section_redirect("products")


@admin_required
@require_POST
def admin_create_user(request):
    form = AdminUserForm(request.POST, require_password=True)
    if form.is_valid():
        try:
            api.create_user(form.cleaned_data, request.session.get("token", ""))
            messages.success(request, "La cuenta se creó correctamente.")
        except api.ApiError as error:
            messages.error(request, error.message)
    else:
        messages.error(request, "Revisa los datos de la cuenta e inténtalo de nuevo.")
    return _admin_section_redirect("users")


@admin_required
@require_POST
def admin_update_user(request, id):
    form = AdminUserForm(request.POST)
    if form.is_valid():
        current_user = request.session.get("user") or {}
        if current_user.get("id") == id and form.cleaned_data["role"] != "administrador":
            messages.error(request, "No puedes quitarte tus propios permisos de administrador.")
            return _admin_section_redirect("users")
        data = {key: value for key, value in form.cleaned_data.items() if key != "password" or value}
        try:
            updated_user = api.update_user(id, data, request.session.get("token", ""))
            if current_user.get("id") == id and isinstance(updated_user, dict):
                request.session["user"] = updated_user
            messages.success(request, "Los datos de la cuenta se actualizaron.")
        except api.ApiError as error:
            messages.error(request, error.message)
    else:
        messages.error(request, "Revisa los datos de la cuenta e inténtalo de nuevo.")
    return _admin_section_redirect("users")


@admin_required
@require_POST
def admin_delete_user(request, id):
    current_user = request.session.get("user") or {}
    if current_user.get("id") == id:
        messages.error(request, "No puedes eliminar tu propia cuenta mientras estás conectado.")
        return _admin_section_redirect("users")
    try:
        api.delete_user(id, request.session.get("token", ""))
        messages.success(request, "La cuenta se eliminó correctamente.")
    except api.ApiError as error:
        messages.error(request, error.message)
    return _admin_section_redirect("users")


# Autenticación de usuarios y administradores


def login_view(request):
    """Página de inicio de sesión minimalista para usuario o administrador."""
    next_url = _safe_next_url(request, request.GET.get("next") or request.POST.get("next"))
    login_failed = False
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            try:
                data = api.login(
                    form.cleaned_data["username"],
                    form.cleaned_data["password"],
                )
                if not isinstance(data, dict):
                    raise api.ApiError("La API devolvió una respuesta inesperada al iniciar sesión.")
                user = data.get("user")
                token = data.get("access_token")
                if not isinstance(user, dict) or not token:
                    raise api.ApiError("La API devolvió una respuesta incompleta al iniciar sesión.")
                request.session["user"] = user
                request.session["token"] = token
                messages.success(request, f"¡Bienvenido, {user.get('full_name') or user.get('username', 'usuario')}!")
                if str(user.get("role", "")).lower() in {"admin", "administrador"}:
                    return redirect("store:admin_dashboard")
                if next_url:
                    return redirect(next_url)
                return redirect("store:catalog")
            except api.ApiError as error:
                messages.error(request, error.message)
                login_failed = error.status_code == 401
    else:
        form = LoginForm()

    return render(
        request,
        "auth/login.html",
        {"form": form, "next": next_url, "login_failed": login_failed},
    )


def register_view(request):
    """Página de creación de cuenta minimalista."""
    next_url = _safe_next_url(request, request.GET.get("next") or request.POST.get("next"))
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                api.register(
                    {
                        "username": form.cleaned_data["username"],
                        "email": form.cleaned_data["email"],
                        "full_name": form.cleaned_data["full_name"],
                        "password": form.cleaned_data["password"],
                    }
                )
                messages.success(request, "Cuenta creada exitosamente. Inicia sesión ahora.")
                query = f"?{urlencode({'next': next_url})}" if next_url else ""
                return redirect(f"{reverse('store:login')}{query}")
            except api.ApiError as error:
                messages.error(request, error.message)
    else:
        form = RegisterForm()

    return render(
        request,
        "auth/register.html",
        {"form": form, "next": next_url},
    )


def logout_view(request):
    """Cierra la sesión del usuario."""
    request.session.flush()
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect("store:home")


def forgot_password_view(request):
    """Muestra el formulario de recuperación de contraseña."""
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            messages.success(
                request,
                "Si existe una cuenta con ese correo, recibirás las instrucciones pronto.",
            )
            return redirect("store:forgot_password")
    else:
        form = PasswordResetRequestForm()
    return render(request, "auth/forgot_password.html", {"form": form})
