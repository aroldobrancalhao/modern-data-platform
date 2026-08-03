from uuid import uuid4

from faker import Faker

from simulator.core.faker_fallback import unique_or_fallback
from simulator.domain.inventory.warehouse_model import Warehouse


class WarehouseGenerator:
    def __init__(self) -> None:
        self._faker = Faker("pt_BR")

    def generate(self) -> Warehouse:
        city = self._faker.city()
        state = self._faker.estado_nome()

        return Warehouse.create(
            code=unique_or_fallback(
                "warehouse.code",
                lambda: self._faker.unique.bothify("WH-########"),
                lambda: f"WH-{uuid4().hex[:8]}",
            ),
            name=f"Distribution Center {city}",
            street=self._faker.street_address(),
            city=city,
            state=state,
            country="Brazil",
        )
