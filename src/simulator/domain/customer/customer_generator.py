from faker import Faker

from simulator.domain.customer.customer_model import Customer


class CustomerGenerator:
    def __init__(self) -> None:
        self._faker = Faker("pt_BR")

    def generate(self) -> Customer:
        return Customer.create(
            first_name=self._faker.first_name(),
            last_name=self._faker.last_name(),
            email=self._faker.unique.email(),
            phone_number=self._faker.cellphone_number(),
            document_number=self._faker.cpf(),
            birth_date=self._faker.date_of_birth(
                minimum_age=18,
                maximum_age=80,
            ),
        )
