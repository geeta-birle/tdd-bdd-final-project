######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

"""
Product API Service Test Suite

Run tests with:
    nosetests
    coverage report -m
"""

import os
import logging
from decimal import Decimal
from unittest import TestCase

from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory


# Disable all but critical errors during normal test run
# Uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

DATABASE_URI = os.getenv(
    "DATABASE_URI",
    "postgresql://postgres:postgres@localhost:5432/postgres",
)
BASE_URL = "/products"


# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()
        db.session.commit()

    def tearDown(self):
        """Runs after each test"""
        db.session.remove()

    # ----------------------------------------------------------
    # Utility: create products
    # ----------------------------------------------------------
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []

        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(
                BASE_URL,
                json=test_product.serialize(),
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test product",
            )

            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)

        return products

    # ----------------------------------------------------------
    # TEST HOME PAGE
    # ----------------------------------------------------------
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn(
            b"Product Catalog Administration",
            response.data,
        )

    # ----------------------------------------------------------
    # TEST HEALTH
    # ----------------------------------------------------------
    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        data = response.get_json()
        self.assertEqual(data["message"], "OK")

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()

        logging.debug(
            "Test Product: %s",
            test_product.serialize(),
        )

        response = self.client.post(
            BASE_URL,
            json=test_product.serialize(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        location = response.headers.get("Location")
        self.assertIsNotNone(location)

        new_product = response.get_json()

        self.assertEqual(
            new_product["name"],
            test_product.name,
        )
        self.assertEqual(
            new_product["description"],
            test_product.description,
        )
        self.assertEqual(
            Decimal(new_product["price"]),
            test_product.price,
        )
        self.assertEqual(
            new_product["available"],
            test_product.available,
        )
        self.assertEqual(
            new_product["category"],
            test_product.category.name,
        )

        # Verify the Location header points to the new Product
        response = self.client.get(location)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        retrieved_product = response.get_json()

        self.assertEqual(
            retrieved_product["id"],
            new_product["id"],
        )
        self.assertEqual(
            retrieved_product["name"],
            test_product.name,
        )

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]

        response = self.client.post(
            BASE_URL,
            json=new_product,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(
            BASE_URL,
            data="bad data",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(
            BASE_URL,
            data={},
            content_type="plain/text",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    # ----------------------------------------------------------
    # TEST LIST ALL
    # ----------------------------------------------------------
    def test_list_all_products(self):
        """It should List all Products"""
        products = self._create_products(count=3)

        response = self.client.get(BASE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.get_json()
        self.assertEqual(len(data), 3)

        returned_ids = [item["id"] for item in data]

        for product in products:
            self.assertIn(product.id, returned_ids)

    def test_list_products_empty(self):
        """It should return an empty list when no Products exist"""
        response = self.client.get(BASE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.get_json(), [])

    # ----------------------------------------------------------
    # TEST READ
    # ----------------------------------------------------------
    def test_read_product(self):
        """It should Read a Product by its ID"""
        product = self._create_products()[0]

        response = self.client.get(
            f"{BASE_URL}/{product.id}",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.get_json()

        self.assertEqual(data["id"], product.id)
        self.assertEqual(data["name"], product.name)
        self.assertEqual(
            data["description"],
            product.description,
        )
        self.assertEqual(
            Decimal(data["price"]),
            product.price,
        )
        self.assertEqual(
            data["available"],
            product.available,
        )
        self.assertEqual(
            data["category"],
            product.category.name,
        )

    def test_read_product_not_found(self):
        """It should return 404 for a missing Product"""
        response = self.client.get(
            f"{BASE_URL}/999999",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # ----------------------------------------------------------
    # TEST UPDATE
    # ----------------------------------------------------------
    def test_update_product(self):
        """It should Update an existing Product"""
        product = self._create_products()[0]
        updated_data = product.serialize()

        updated_data["name"] = "Updated Product"
        updated_data["description"] = "Updated description"
        updated_data["price"] = "25.50"
        updated_data["available"] = not product.available

        response = self.client.put(
            f"{BASE_URL}/{product.id}",
            json=updated_data,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.get_json()

        self.assertEqual(data["id"], product.id)
        self.assertEqual(data["name"], "Updated Product")
        self.assertEqual(
            data["description"],
            "Updated description",
        )
        self.assertEqual(
            Decimal(data["price"]),
            Decimal("25.50"),
        )
        self.assertEqual(
            data["available"],
            not product.available,
        )

        # Confirm changes were persisted
        response = self.client.get(
            f"{BASE_URL}/{product.id}",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.get_json()["name"],
            "Updated Product",
        )

    def test_update_product_not_found(self):
        """It should return 404 when updating a missing Product"""
        product_data = ProductFactory().serialize()

        response = self.client.put(
            f"{BASE_URL}/999999",
            json=product_data,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_update_product_no_content_type(self):
        """It should reject an update without Content-Type"""
        response = self.client.put(
            f"{BASE_URL}/1",
            data="bad data",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    def test_update_product_wrong_content_type(self):
        """It should reject an update with the wrong Content-Type"""
        response = self.client.put(
            f"{BASE_URL}/1",
            data="bad data",
            content_type="plain/text",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    # ----------------------------------------------------------
    # TEST DELETE
    # ----------------------------------------------------------
    def test_delete_product(self):
        """It should Delete a Product"""
        product = self._create_products()[0]

        response = self.client.delete(
            f"{BASE_URL}/{product.id}",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        # Verify the Product was deleted
        response = self.client.get(
            f"{BASE_URL}/{product.id}",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete_product_not_found(self):
        """It should return 404 when deleting a missing Product"""
        response = self.client.delete(
            f"{BASE_URL}/999999",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # ----------------------------------------------------------
    # UTILITY
    # ----------------------------------------------------------
    def get_product_count(self):
        """Return the current number of Products"""
        response = self.client.get(BASE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.get_json()
        return len(data)
