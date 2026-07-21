from faker import Faker

from simulator.domain.catalog.seller_model import Category


class CategoryGenerator:
    _CATEGORIES = [
        "Electronics",
        "Home & Kitchen",
        "Computers",
        "Fashion",
        "Sports",
        "Health",
        "Beauty",
        "Automotive",
        "Books",
        "Toys",
    ]

    def __init__(self) -> None:
        self._faker = Faker()

    def generate(self) -> Category:
        name = self._faker.random_element(self._CATEGORIES)

        return Category.create(
            name=name,
            description=f"{name} products",
        )
