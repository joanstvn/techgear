from django.urls import path

from store import views

app_name = "store"

urlpatterns = [
    # Landing
    path("", views.home, name="home"),
    # Catálogo público
    path("catalogo/", views.catalog, name="catalog"),
    path("producto/<str:id>/", views.product_detail, name="product_detail"),
    path("producto/<str:id>/pedido/", views.create_order, name="create_order"),
    # Carrito y pedidos de clientes
    path("carrito/", views.cart_view, name="cart"),
    path("carrito/agregar/<str:id>/", views.cart_add, name="cart_add"),
    path("carrito/actualizar/<str:id>/", views.cart_update, name="cart_update"),
    path("carrito/quitar/<str:id>/", views.cart_remove, name="cart_remove"),
    path("carrito/confirmar/", views.cart_checkout, name="cart_checkout"),
    path("mis-pedidos/", views.my_orders, name="my_orders"),
    path("mis-pedidos/<str:id>/cancelar/", views.cancel_my_order, name="cancel_my_order"),
    # Autenticación
    path("login/", views.login_view, name="login"),
    path("registro/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("recuperar-contrasena/", views.forgot_password_view, name="forgot_password"),
    # Administración
    path("administracion/", views.admin_dashboard, name="admin_dashboard"),
    path("administracion/productos/crear/", views.admin_create_product, name="admin_create_product"),
    path("administracion/productos/<str:id>/editar/", views.admin_update_product, name="admin_update_product"),
    path("administracion/productos/<str:id>/eliminar/", views.admin_delete_product, name="admin_delete_product"),
    path("administracion/usuarios/crear/", views.admin_create_user, name="admin_create_user"),
    path("administracion/usuarios/<str:id>/editar/", views.admin_update_user, name="admin_update_user"),
    path("administracion/usuarios/<str:id>/eliminar/", views.admin_delete_user, name="admin_delete_user"),
    path("administracion/pedidos/<str:id>/estado/", views.admin_update_order_status, name="admin_update_order_status"),
]
