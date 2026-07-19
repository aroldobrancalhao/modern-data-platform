from simulator.core.database import Database
from simulator.domain.catalog.category_generator import CategoryGenerator
from simulator.domain.catalog.category_repository import CategoryRepository
from simulator.domain.catalog.seller_model import Category


class CategoryService:
    def __init__(self) -> None:
        self._database = Database()
        self._generator = CategoryGenerator()

    def create_category(self) -> Category:
        category = self._generator.generate()

        with self._database.connection() as connection:
            repository = CategoryRepository(connection)
            repository.insert(category)

        return category