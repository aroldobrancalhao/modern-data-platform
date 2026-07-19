from faker import Faker

from simulator.domain.customer.address_model import CustomerAddress


class CustomerAddressGenerator:
    def __init__(self) -> None:
        self._faker = Faker("pt_BR")

    def generate(
        self,
        customer_id,
    ) -> CustomerAddress:
        complement = (
            f"Apto {self._faker.random_int(min=1, max=999)}"
            if self._faker.boolean(chance_of_getting_true=30)
            else None
        )

        district = (
            self._faker.word().title()
            if self._faker.boolean(chance_of_getting_true=90)
            else None
        )

        return CustomerAddress.create(
            customer_id=customer_id,
            street=self._faker.street_name(),
            street_number=str(self._faker.building_number()),
            complement=complement,
            district=district,
            city=self._faker.city(),
            state=self._faker.estado_sigla(),
            postal_code=self._faker.postcode(),
        )