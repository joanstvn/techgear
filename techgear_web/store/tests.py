from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

PRODUCT = {
    "id": "6701f2a8b4c9d1e2f3a4b5c8",
    "name": "RoboExplora Mini",
    "description": "Robot educativo para niños.",
    "price": 289.90,
    "stock": 14,
    "category": "Robótica educativa",
    "image": "https://example.com/robo.png",
}


class CatalogTests(TestCase):
    @patch("store.views.api.list_products")
    def test_home_renders_landing(self, list_products):
        list_products.return_value = [PRODUCT]
        response = self.client.get(reverse("store:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TechGear")

    @patch("store.views.api.list_products")
    def test_catalog_renders(self, list_products):
        list_products.return_value = [PRODUCT]
        response = self.client.get(reverse("store:catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RoboExplora Mini")

    @patch("store.views.api.list_products")
    def test_catalog_search(self, list_products):
        list_products.return_value = [PRODUCT]
        response = self.client.get(reverse("store:catalog") + "?q=robo")
        self.assertContains(response, "RoboExplora Mini")

    @patch("store.views.api.list_products")
    def test_catalog_filter_category(self, list_products):
        list_products.return_value = [PRODUCT]
        response = self.client.get(reverse("store:catalog") + "?categoria=Robótica+educativa")
        self.assertContains(response, "RoboExplora Mini")

    @patch("store.views.api.get_product")
    def test_product_detail(self, get_product):
        get_product.return_value = PRODUCT
        response = self.client.get(reverse("store:product_detail", args=[PRODUCT["id"]]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RoboExplora Mini")

    @patch("store.views.api.create_order")
    @patch("store.views.api.get_product")
    def test_create_order(self, get_product, create_order):
        get_product.return_value = PRODUCT
        create_order.return_value = {"id": "order123"}
        response = self.client.post(
            reverse("store:create_order", args=[PRODUCT["id"]]),
            {
                "customer_name": "Juan",
                "customer_email": "juan@example.com",
                "quantity": 1,
            },
        )
        self.assertRedirects(
            response,
            reverse("store:product_detail", args=[PRODUCT["id"]]),
            fetch_redirect_response=False,
        )
