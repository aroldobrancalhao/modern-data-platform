from faker import Faker

from simulator.domain.inventory.warehouse_model import Warehouse


class WarehouseGenerator:
    def __init__(self) -> None:
        self._faker = Faker("pt_BR")

    def generate(self) -> Warehouse:
        city = self._faker.city()
        state = self._faker.estado_nome()

        return Warehouse.create(
            code=self._faker.unique.bothify("WH-####"),
            name=f"Distribution Center {city}",
            street=self._faker.street_address(),
            city=city,
            state=state,
            country="Brazil",
        )
