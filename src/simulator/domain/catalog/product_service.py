from simulator.core.database import Database

from simulator.domain.catalog.category_repository import CategoryRepository
from simulator.domain.catalog.product_generator import ProductGenerator
from simulator.domain.catalog.product_model import Product
from simulator.domain.catalog.product_repository import ProductRepository
from simulator.domain.catalog.seller_repository import SellerRepository


class ProductService:
    def __init__(self) -> None:
        self._database = Database()
        self._generator = ProductGenerator()

    def create_product(self) -> Product:
        with self._database.connection() as connection:
            seller_repository = SellerRepository(connection)
            category_repository = CategoryRepository(connection)

            seller_id = seller_repository.get_random_id()
            category_id = category_repository.get_random_id()

            if seller_id is None:
                raise ValueError("No seller found.")

            if category_id is None:
                raise ValueError("No category found.")

            product = self._generator.generate(
                seller_id=seller_id,
                category_id=category_id,
            )

            repository = ProductRepository(connection)
            repository.insert(product)

        return product
