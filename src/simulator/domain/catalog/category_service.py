from psycopg import Connection

from simulator.core.reference_pool import ReferencePool
from simulator.core.unique_insert import insert_with_unique_retry
from simulator.domain.catalog.category_generator import CategoryGenerator
from simulator.domain.catalog.category_repository import CategoryRepository
from simulator.domain.catalog.seller_model import Category


class CategoryService:
    def __init__(self) -> None:
        self._generator = CategoryGenerator()

    def create_category(self, connection: Connection, pool: ReferencePool) -> Category:
        repository = CategoryRepository(connection)

        category = insert_with_unique_retry(
            "category",
            self._generator.generate,
            repository.insert,
        )

        pool.category_ids.append(category.category_id)

        return category
