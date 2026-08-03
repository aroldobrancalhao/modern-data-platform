from psycopg import Connection

from simulator.core.reference_pool import ReferencePool
from simulator.core.unique_insert import insert_with_unique_retry
from simulator.domain.catalog.product_generator import ProductGenerator
from simulator.domain.catalog.product_model import Product
from simulator.domain.catalog.product_repository import ProductRepository


class ProductService:
    def __init__(self) -> None:
        self._generator = ProductGenerator()

    def create_product(self, connection: Connection, pool: ReferencePool) -> Product:
        seller_id = pool.random_seller_id()
        category_id = pool.random_category_id()

        if seller_id is None:
            raise ValueError("No seller found.")

        if category_id is None:
            raise ValueError("No category found.")

        repository = ProductRepository(connection)

        product = insert_with_unique_retry(
            "product",
            lambda: self._generator.generate(
                seller_id=seller_id,
                category_id=category_id,
            ),
            repository.insert,
        )

        pool.product_ids.append(product.product_id)

        return product
