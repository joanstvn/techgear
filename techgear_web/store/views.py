from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from store import api
from store.decorators import (
    admin_required_session,
    get_access_token,
    get_session_user,
)
from store.forms import (
    LoginForm,
    OrderForm,
    OrderStatusForm,
    ProductForm,
    UserForm,
)


def _handle_api_error(request, error: api.ApiError):
    """Muestra el error de la API y cierra la sesión si el token expiró."""
    if error.status_code == 401 and get_access_token(request):
        request.session.flush()
        messages.error(request, "Tu sesión expiró. Inicia sesión nuevamente.")
        return redirect("store:login")
    messages.error(request, error.message)
    return None


def _safe_next_url(request) -> str | None:
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return None


# Autenticación


def login_view(request):
    if get_access_token(request):
        if (get_session_user(request) or {}).get("role", "").lower() in {"admin", "administrador"}:
            return redirect("store:panel")
        return redirect("store:catalog")

    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            data = api.login(
                form.cleaned_data["username"],
                form.cleaned_data["password"],
            )
        except api.ApiError as error:
            messages.error(request, error.message)
        else:
            request.session.cycle_key()
            request.session["access_token"] = data["access_token"]
            request.session["user"] = data["user"]
            request.session["is_admin"] = str(data["user"].get("role", "")).lower() in {
                "admin",
                "administrador",
            }
            messages.success(
                request,
                f"Bienvenido de nuevo, {data['user'].get('full_name') or data['user'].get('username')}.",
            )
            next_url = _safe_next_url(request)
            if next_url:
                return redirect(next_url)
            return redirect("store:panel" if request.session["is_admin"] else "store:catalog")

    return render(request, "store/login.html", {"form": form, "next": _safe_next_url(request) or ""})


def logout_view(request):
    request.session.flush()
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("store:catalog")


# Catálogo público


def catalog(request):
    try:
        products = api.list_products()
    except api.ApiError as error:
        messages.error(request, error.message)
        products = []

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
        "store/catalog.html",
        {
            "products": products,
            "categories": categories,
            "query": query,
            "selected_category": category,
        },
    )


def product_detail(request, id: str):
    try:
        product = api.get_product(id)
    except api.ApiError as error:
        messages.error(request, error.message)
        return redirect("store:catalog")

    form = OrderForm(request.POST or None)
    return render(
        request,
        "store/product_detail.html",
        {"product": product, "form": form},
    )


@require_POST
def create_order(request, id: str):
    try:
        product = api.get_product(id)
    except api.ApiError as error:
        messages.error(request, error.message)
        return redirect("store:catalog")

    form = OrderForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "store/product_detail.html",
            {"product": product, "form": form},
        )

    quantity = form.cleaned_data["quantity"]
    total_price = round(float(product.get("price", 0)) * quantity, 2)

    try:
        api.create_order(
            {
                "customer_name": form.cleaned_data["customer_name"],
                "customer_email": form.cleaned_data["customer_email"],
                "product": product.get("name"),
                "quantity": quantity,
                "total_price": total_price,
                "status": "pendiente",
            }
        )
    except api.ApiError as error:
        messages.error(request, error.message)
        return render(
            request,
            "store/product_detail.html",
            {"product": product, "form": form},
        )

    messages.success(
        request,
        f"Pedido de {quantity} unidad(es) de '{product.get('name')}' registrado correctamente.",
    )
    return redirect("store:product_detail", id=id)


# Panel de catálogo (requiere sesión)


@admin_required_session
def panel_catalog(request):
    try:
        products = api.list_products()
    except api.ApiError as error:
        response = _handle_api_error(request, error)
        if response:
            return response
        products = []

    return render(request, "store/panel/catalog.html", {"products": products})


@admin_required_session
def product_create(request):
    form = ProductForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            api.create_product(form.to_api_data(), token=get_access_token(request))
        except api.ApiError as error:
            response = _handle_api_error(request, error)
            if response:
                return response
        else:
            messages.success(request, "Producto creado correctamente.")
            return redirect("store:panel")

    return render(
        request,
        "store/panel/product_form.html",
        {"form": form, "title": "Nuevo producto", "submit_label": "Crear producto"},
    )


@admin_required_session
def product_edit(request, id: str):
    try:
        product = api.get_product(id)
    except api.ApiError as error:
        response = _handle_api_error(request, error)
        if response:
            return response
        return redirect("store:panel")

    initial = {
        "name": product.get("name"),
        "description": product.get("description"),
        "price": product.get("price"),
        "stock": product.get("stock"),
        "category": product.get("category"),
        "image": product.get("image"),
    }
    form = ProductForm(request.POST or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        try:
            api.update_product(id, form.to_api_data(), token=get_access_token(request))
        except api.ApiError as error:
            response = _handle_api_error(request, error)
            if response:
                return response
        else:
            messages.success(request, "Producto actualizado correctamente.")
            return redirect("store:panel")

    return render(
        request,
        "store/panel/product_form.html",
        {"form": form, "product": product, "title": "Editar producto", "submit_label": "Guardar cambios"},
    )


@require_POST
@admin_required_session
def product_delete(request, id: str):
    try:
        api.delete_product(id, token=get_access_token(request))
    except api.ApiError as error:
        response = _handle_api_error(request, error)
        if response:
            return response
    else:
        messages.success(request, "Producto eliminado correctamente.")
    return redirect("store:panel")


# Panel de administración (requiere rol administrador)


@admin_required_session
def panel_admin(request):
    stats = {"products": 0, "users": 0, "orders": 0, "pending": 0}
    orders = []

    try:
        stats["products"] = len(api.list_products())
    except api.ApiError:
        pass

    try:
        stats["users"] = len(api.list_users(get_access_token(request)))
    except api.ApiError as error:
        if error.status_code == 401:
            return _handle_api_error(request, error) or redirect("store:login")

    try:
        orders = api.list_orders()
        stats["orders"] = len(orders)
        stats["pending"] = sum(
            1 for order in orders if str(order.get("status", "")).lower() == "pendiente"
        )
    except api.ApiError:
        pass

    return render(
        request,
        "store/panel/dashboard.html",
        {"stats": stats, "recent_orders": orders[-5:][::-1]},
    )


@admin_required_session
def user_list(request):
    try:
        users = api.list_users(get_access_token(request))
    except api.ApiError as error:
        response = _handle_api_error(request, error)
        if response:
            return response
        users = []

    return render(
        request,
        "store/panel/users.html",
        {"users": users, "current_user_id": (get_session_user(request) or {}).get("id")},
    )


@admin_required_session
def user_create(request):
    form = UserForm(request.POST or None, require_password=True)

    if request.method == "POST" and form.is_valid():
        try:
            api.create_user(form.to_api_data(), token=get_access_token(request))
        except api.ApiError as error:
            response = _handle_api_error(request, error)
            if response:
                return response
        else:
            messages.success(request, "Usuario creado correctamente.")
            return redirect("store:users")

    return render(
        request,
        "store/panel/user_form.html",
        {"form": form, "title": "Nuevo usuario", "submit_label": "Crear usuario"},
    )


@admin_required_session
def user_edit(request, id: str):
    try:
        user = api.get_user(id, get_access_token(request))
    except api.ApiError as error:
        response = _handle_api_error(request, error)
        if response:
            return response
        return redirect("store:users")

    initial = {
        "username": user.get("username"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "role": "administrador"
        if str(user.get("role", "")).lower() in {"admin", "administrador"}
        else "cliente",
    }
    form = UserForm(request.POST or None, initial=initial, require_password=False)

    if request.method == "POST" and form.is_valid():
        try:
            api.update_user(id, form.to_api_data(), token=get_access_token(request))
        except api.ApiError as error:
            response = _handle_api_error(request, error)
            if response:
                return response
        else:
            if (get_session_user(request) or {}).get("id") == id:
                request.session["user"] = api.get_user(id, get_access_token(request))
                request.session["is_admin"] = request.session["user"].get("role") in {
                    "admin",
                    "administrador",
                }
            messages.success(request, "Usuario actualizado correctamente.")
            return redirect("store:users")

    return render(
        request,
        "store/panel/user_form.html",
        {"form": form, "user": user, "title": "Editar usuario", "submit_label": "Guardar cambios"},
    )


@require_POST
@admin_required_session
def user_delete(request, id: str):
    if (get_session_user(request) or {}).get("id") == id:
        messages.error(request, "No puedes eliminar tu propio usuario.")
        return redirect("store:users")

    try:
        api.delete_user(id, get_access_token(request))
    except api.ApiError as error:
        response = _handle_api_error(request, error)
        if response:
            return response
    else:
        messages.success(request, "Usuario eliminado correctamente.")
    return redirect("store:users")


@admin_required_session
def order_list(request):
    try:
        orders = api.list_orders()
    except api.ApiError as error:
        response = _handle_api_error(request, error)
        if response:
            return response
        orders = []

    return render(
        request,
        "store/panel/orders.html",
        {"orders": orders, "status_form": OrderStatusForm()},
    )


@require_POST
@admin_required_session
def order_update_status(request, id: str):
    form = OrderStatusForm(request.POST)
    if not form.is_valid():
        messages.error(request, "El estado seleccionado no es válido.")
        return redirect("store:orders")

    try:
        api.update_order_status(id, form.cleaned_data["status"])
    except api.ApiError as error:
        response = _handle_api_error(request, error)
        if response:
            return response
    else:
        messages.success(request, "Estado del pedido actualizado correctamente.")
    return redirect("store:orders")
