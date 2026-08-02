from psycopg import Connection

from simulator.domain.catalog.category_generator import CategoryGenerator
from simulator.domain.catalog.category_repository import CategoryRepository
from simulator.domain.catalog.seller_model import Category


class CategoryService:
    def __init__(self) -> None:
        self._generator = CategoryGenerator()

    def create_category(self, connection: Connection) -> Category:
        category = self._generator.generate()

        repository = CategoryRepository(connection)
        repository.insert(category)

        return category
