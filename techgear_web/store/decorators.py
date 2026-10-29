"""Utilidades para manejar la sesión del usuario autenticado con JWT."""

from functools import wraps
from typing import Callable

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

ADMIN_ROLES = {"admin", "administrador"}


def get_session_user(request) -> dict | None:
    """Devuelve el usuario guardado en la sesión de Django, si existe."""
    return request.session.get("user")


def get_access_token(request) -> str | None:
    """Devuelve el token JWT almacenado en la sesión de Django."""
    return request.session.get("access_token")


def is_admin(request) -> bool:
    user = get_session_user(request)
    if not user:
        return False
    return str(user.get("role", "")).strip().lower() in ADMIN_ROLES


def _login_redirect(request):
    login_url = reverse("store:login")
    if request.path and request.path != reverse("store:catalog"):
        return redirect(f"{login_url}?next={request.path}")
    return redirect(login_url)


def login_required_session(view: Callable) -> Callable:
    """Redirige al login cuando no hay un token JWT en la sesión."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not get_access_token(request):
            messages.warning(request, "Inicia sesión para continuar.")
            return _login_redirect(request)
        return view(request, *args, **kwargs)

    return wrapper


def admin_required_session(view: Callable) -> Callable:
    """Restringe el acceso a usuarios con rol de administrador."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not get_access_token(request):
            messages.warning(request, "Inicia sesión para continuar.")
            return _login_redirect(request)
        if not is_admin(request):
            messages.error(request, "No tienes permisos de administrador.")
            return redirect("store:catalog")
        return view(request, *args, **kwargs)

    return wrapper
