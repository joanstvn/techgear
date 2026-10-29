from django.urls import path

from store import views

app_name = "store"

urlpatterns = [
    # Catálogo público
    path("", views.catalog, name="catalog"),
    path("producto/<str:id>/", views.product_detail, name="product_detail"),
    path("producto/<str:id>/pedido/", views.create_order, name="create_order"),
    # Autenticación
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Panel de catálogo
    path("panel/", views.panel_catalog, name="panel"),
    path("panel/productos/nuevo/", views.product_create, name="product_create"),
    path("panel/productos/<str:id>/editar/", views.product_edit, name="product_edit"),
    path("panel/productos/<str:id>/eliminar/", views.product_delete, name="product_delete"),
    # Panel de administración
    path("panel/admin/", views.panel_admin, name="panel_admin"),
    path("panel/admin/usuarios/", views.user_list, name="users"),
    path("panel/admin/usuarios/nuevo/", views.user_create, name="user_create"),
    path("panel/admin/usuarios/<str:id>/editar/", views.user_edit, name="user_edit"),
    path("panel/admin/usuarios/<str:id>/eliminar/", views.user_delete, name="user_delete"),
    path("panel/admin/pedidos/", views.order_list, name="orders"),
    path("panel/admin/pedidos/<str:id>/estado/", views.order_update_status, name="order_update_status"),
]
