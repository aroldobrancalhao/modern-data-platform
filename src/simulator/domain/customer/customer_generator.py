from uuid import uuid4

from faker import Faker

from simulator.core.faker_fallback import unique_or_fallback
from simulator.domain.customer.customer_model import Customer


class CustomerGenerator:
    def __init__(self) -> None:
        self._faker = Faker("pt_BR")

    def generate(self) -> Customer:
        return Customer.create(
            first_name=self._faker.first_name(),
            last_name=self._faker.last_name(),
            email=unique_or_fallback(
                "customer.email",
                self._entropic_email,
                lambda: f"{uuid4().hex[:12]}@example.com",
            ),
            phone_number=self._faker.cellphone_number(),
            document_number=self._faker.cpf(),
            birth_date=self._faker.date_of_birth(
                minimum_age=18,
                maximum_age=80,
            ),
        )

    def _entropic_email(self) -> str:
        """
        `faker.email()`'s realistic `firstname.lastname@domain` local
        parts have a far shallower effective value space than they
        look like they should -- measured empirically at ~22.6%
        collision rate against ~28k real rows already in Postgres
        (same class of problem as the original `warehouse.code`
        crash: format looks fine, actual entropy is not). Appending an
        8-hex-char suffix (same width already used for warehouse.code/
        product.sku/order.order_number/shipment.tracking_code/
        payment.transaction_code) pushes the collision probability to
        effectively zero regardless of how large the customers table
        grows, while the address still reads as a real email.
        """
        local_part, domain = self._faker.unique.email().split("@", 1)

        return f"{local_part}.{uuid4().hex[:8]}@{domain}"
