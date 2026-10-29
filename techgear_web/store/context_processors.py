def session_user(request):
    """Expone el usuario de la sesión y su rol a todas las plantillas."""
    user = request.session.get("user")
    role = str((user or {}).get("role", "")).strip().lower()
    return {
        "session_user": user,
        "is_admin": role in {"admin", "administrador"},
    }
