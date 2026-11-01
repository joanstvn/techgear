from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from store.api import ApiError


ADMIN_USER = {
    "id": "6701f2a8b4c9d1e2f3a4b5c6",
    "username": "admin",
    "email": "admin@techgear.com",
    "full_name": "Administrador TechGear",
    "role": "administrador",
}

CLIENT_USER = {
    "id": "6701f2a8b4c9d1e2f3a4b5c7",
    "username": "cliente",
    "email": "cliente@techgear.com",
    "full_name": "Cliente TechGear",
    "role": "cliente",
}

PRODUCT = {
    "id": "6701f2a8b4c9d1e2f3a4b5c8",
    "name": "Teclado Mecánico RGB",
    "description": "Teclado con switches táctiles",
    "price": 79.99,
    "stock": 10,
    "category": "Periféricos",
    "image": "https://example.com/teclado.jpg",
}


def login_session(client, user=ADMIN_USER, token="token-de-prueba"):
    session = client.session
    session["access_token"] = token
    session["user"] = user
    session.save()


class CatalogTests(TestCase):
    @patch("store.views.api.list_products")
    def test_home_renders_landing(self, list_products):
        list_products.return_value = [PRODUCT]

        response = self.client.get(reverse("store:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "techgear")
        self.assertContains(response, PRODUCT["name"])
        self.assertContains(response, "verificada")

    @patch("store.views.api.list_products")
    def test_catalog_lists_products(self, list_products):
        list_products.return_value = [PRODUCT]

        response = self.client.get(reverse("store:catalog"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, PRODUCT["name"])
        self.assertContains(response, "Periféricos")

    @patch("store.views.api.list_products")
    def test_catalog_filters_by_query(self, list_products):
        list_products.return_value = [PRODUCT]

        response = self.client.get(reverse("store:catalog"), {"q": "teclado"})

        self.assertContains(response, PRODUCT["name"])

    @patch("store.views.api.get_product")
    def test_product_detail_renders(self, get_product):
        get_product.return_value = PRODUCT

        response = self.client.get(reverse("store:product_detail", args=[PRODUCT["id"]]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Realizar pedido")


class AuthenticationTests(TestCase):
    @patch("store.views.api.login")
    def test_login_creates_session_for_admin(self, login):
        login.return_value = {
            "access_token": "jwt-de-prueba",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": ADMIN_USER,
        }

        response = self.client.post(
            reverse("store:login"),
            {"username": "admin", "password": "admin123"},
        )

        self.assertRedirects(
            response, reverse("store:panel"), fetch_redirect_response=False
        )
        self.assertEqual(self.client.session["access_token"], "jwt-de-prueba")
        self.assertEqual(self.client.session["user"]["role"], "administrador")

    @patch("store.views.api.login")
    def test_login_shows_error_with_invalid_credentials(self, login):
        login.side_effect = ApiError("Usuario o contraseña incorrectos", 401)

        response = self.client.post(
            reverse("store:login"),
            {"username": "admin", "password": "incorrecta"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Usuario o contraseña incorrectos")
        self.assertNotIn("access_token", self.client.session)

    def test_logout_clears_session(self):
        login_session(self.client)

        response = self.client.get(reverse("store:logout"))

        self.assertRedirects(
            response, reverse("store:catalog"), fetch_redirect_response=False
        )
        self.assertNotIn("access_token", self.client.session)


class PanelPermissionTests(TestCase):
    def test_panel_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse("store:panel"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("store:login"), response.url)

    def test_admin_panel_rejects_non_admin_user(self):
        login_session(self.client, user=CLIENT_USER)

        response = self.client.get(reverse("store:panel_admin"))

        self.assertRedirects(
            response, reverse("store:catalog"), fetch_redirect_response=False
        )

    @patch("store.views.api.list_products")
    def test_admin_panel_renders_stats(self, list_products):
        list_products.return_value = [PRODUCT]
        login_session(self.client)

        with patch("store.views.api.list_users", return_value=[ADMIN_USER]), patch(
            "store.views.api.list_orders", return_value=[]
        ):
            response = self.client.get(reverse("store:panel_admin"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resumen general")


class ProductManagementTests(TestCase):
    def setUp(self):
        login_session(self.client)

    @patch("store.views.api.create_product")
    def test_create_product_redirects_to_panel(self, create_product):
        create_product.return_value = PRODUCT

        response = self.client.post(
            reverse("store:product_create"),
            {
                "name": PRODUCT["name"],
                "description": PRODUCT["description"],
                "price": "79.99",
                "stock": "10",
                "category": PRODUCT["category"],
                "image": PRODUCT["image"],
            },
        )

        self.assertRedirects(
            response, reverse("store:panel"), fetch_redirect_response=False
        )
        create_product.assert_called_once()
        self.assertEqual(create_product.call_args.args[0]["name"], PRODUCT["name"])

    @patch("store.views.api.delete_product")
    def test_delete_product(self, delete_product):
        delete_product.return_value = {"message": "ok"}

        response = self.client.post(
            reverse("store:product_delete", args=[PRODUCT["id"]])
        )

        self.assertRedirects(
            response, reverse("store:panel"), fetch_redirect_response=False
        )
        delete_product.assert_called_once()


class UserManagementTests(TestCase):
    def setUp(self):
        login_session(self.client)

    def test_cannot_delete_own_user(self):
        response = self.client.post(
            reverse("store:user_delete", args=[ADMIN_USER["id"]])
        )

        self.assertRedirects(
            response, reverse("store:users"), fetch_redirect_response=False
        )

    @patch("store.views.api.create_user")
    def test_create_user(self, create_user):
        create_user.return_value = CLIENT_USER

        response = self.client.post(
            reverse("store:user_create"),
            {
                "username": "cliente",
                "email": "cliente@techgear.com",
                "full_name": "Cliente TechGear",
                "role": "cliente",
                "password": "secreto123",
            },
        )

        self.assertRedirects(
            response, reverse("store:users"), fetch_redirect_response=False
        )
        self.assertEqual(create_user.call_args.args[0]["password"], "secreto123")


class OrderTests(TestCase):
    @patch("store.views.api.create_order")
    @patch("store.views.api.get_product")
    def test_create_order_from_catalog(self, get_product, create_order):
        get_product.return_value = PRODUCT
        create_order.return_value = {"id": "pedido-1"}

        response = self.client.post(
            reverse("store:create_order", args=[PRODUCT["id"]]),
            {
                "customer_name": "Carlos Rodríguez",
                "customer_email": "carlos@example.com",
                "quantity": "2",
            },
        )

        self.assertRedirects(
            response,
            reverse("store:product_detail", args=[PRODUCT["id"]]),
            fetch_redirect_response=False,
        )
        payload = create_order.call_args.args[0]
        self.assertEqual(payload["quantity"], 2)
        self.assertEqual(payload["total_price"], 159.98)
