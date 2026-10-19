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

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m
"""

import os
import logging
import unittest
from decimal import Decimal

from service.models import Product, Category, DataValidationError, db
from service import app
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
# PRODUCT MODEL TEST CASES
######################################################################

# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ##################################################################
    # BASIC CRUD TESTS
    ##################################################################

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(
            name="Fedora",
            description="A red hat",
            price=12.50,
            available=True,
            category=Category.CLOTHS,
        )

        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertIsNotNone(product)
        self.assertIsNone(product.id)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])

        product = ProductFactory()
        product.id = None
        product.create()

        self.assertIsNotNone(product.id)

        products = Product.all()
        self.assertEqual(len(products), 1)

        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    def test_read_a_product(self):
        """It should Read a Product"""
        product = ProductFactory()
        product.create()

        found_product = Product.find(product.id)

        self.assertIsNotNone(found_product)
        self.assertEqual(found_product.id, product.id)
        self.assertEqual(found_product.name, product.name)
        self.assertEqual(found_product.description, product.description)
        self.assertEqual(found_product.available, product.available)
        self.assertEqual(found_product.category, product.category)

    def test_update_a_product(self):
        """It should Update a Product"""
        product = ProductFactory()
        product.create()

        product.name = "Updated Product"
        product.description = "Updated description"
        product.price = Decimal("99.99")
        product.available = False
        product.category = Category.TOOLS
        product.update()

        found_product = Product.find(product.id)

        self.assertEqual(found_product.name, "Updated Product")
        self.assertEqual(
            found_product.description, "Updated description"
        )
        self.assertEqual(
            Decimal(found_product.price), Decimal("99.99")
        )
        self.assertFalse(found_product.available)
        self.assertEqual(found_product.category, Category.TOOLS)

    def test_delete_a_product(self):
        """It should Delete a Product"""
        product = ProductFactory()
        product.create()

        product_id = product.id
        product.delete()

        self.assertIsNone(Product.find(product_id))
        self.assertEqual(Product.all(), [])

    def test_list_all_products(self):
        """It should List All Products"""
        products = ProductFactory.create_batch(5)

        for product in products:
            product.create()

        found_products = Product.all()
        self.assertEqual(len(found_products), 5)

    ##################################################################
    # SEARCH TESTS
    ##################################################################

    def test_find_product_by_name(self):
        """It should Find Products by Name"""
        product = Product(
            name="Hammer",
            description="A steel hammer",
            price=Decimal("15.00"),
            available=True,
            category=Category.TOOLS,
        )
        product.create()

        found_products = Product.find_by_name("Hammer").all()

        self.assertEqual(len(found_products), 1)
        self.assertEqual(found_products[0].name, "Hammer")

    def test_find_product_by_category(self):
        """It should Find Products by Category"""
        product1 = Product(
            name="Hammer",
            description="A steel hammer",
            price=Decimal("15.00"),
            available=True,
            category=Category.TOOLS,
        )
        product2 = Product(
            name="Apple",
            description="A fresh apple",
            price=Decimal("2.00"),
            available=True,
            category=Category.FOOD,
        )

        product1.create()
        product2.create()

        found_products = Product.find_by_category(Category.TOOLS).all()

        self.assertEqual(len(found_products), 1)
        self.assertEqual(found_products[0].name, "Hammer")
        self.assertEqual(found_products[0].category, Category.TOOLS)

    def test_find_products_by_availability(self):
        """It should Find Products by Availability"""
        product1 = Product(
            name="Available Product",
            description="In stock",
            price=Decimal("10.00"),
            available=True,
            category=Category.HOUSEWARES,
        )
        product2 = Product(
            name="Unavailable Product",
            description="Out of stock",
            price=Decimal("20.00"),
            available=False,
            category=Category.HOUSEWARES,
        )

        product1.create()
        product2.create()

        found_products = Product.find_by_availability(True).all()

        self.assertEqual(len(found_products), 1)
        self.assertEqual(found_products[0].name, "Available Product")
        self.assertTrue(found_products[0].available)

    ##################################################################
    # ADDITIONAL VALIDATION AND COVERAGE TESTS
    ##################################################################

    def test_update_product_without_id(self):
        """It should reject updating a product without an ID"""
        product = ProductFactory()
        product.id = None

        with self.assertRaises(DataValidationError):
            product.update()

    def test_deserialize_invalid_available(self):
        """It should reject a non-boolean available value"""
        product = Product()

        data = {
            "name": "Test Product",
            "description": "A test product",
            "price": "10.00",
            "available": "yes",
            "category": "TOOLS",
        }

        with self.assertRaises(DataValidationError):
            product.deserialize(data)

    def test_deserialize_invalid_category(self):
        """It should reject an invalid category"""
        product = Product()

        data = {
            "name": "Test Product",
            "description": "A test product",
            "price": "10.00",
            "available": True,
            "category": "INVALID_CATEGORY",
        }

        with self.assertRaises(DataValidationError):
            product.deserialize(data)

    def test_deserialize_none_data(self):
        """It should reject a missing request body"""
        product = Product()

        with self.assertRaises(DataValidationError):
            product.deserialize(None)

    def test_find_product_by_price(self):
        """It should find products using a string price"""
        product = Product(
            name="Price Test",
            description="Product for price search",
            price=Decimal("15.00"),
            available=True,
            category=Category.TOOLS,
        )
        product.create()

        found_products = Product.find_by_price('"15.00"').all()

        self.assertEqual(len(found_products), 1)
        self.assertEqual(found_products[0].name, "Price Test")
