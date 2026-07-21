from faker import Faker

from simulator.domain.catalog.seller_model import Seller


class SellerGenerator:
    def __init__(self) -> None:
        self._faker = Faker("pt_BR")

    def generate(self) -> Seller:
        company_name = self._faker.company()

        return Seller.create(
            company_name=company_name,
            trade_name=company_name,
            document_number=self._faker.cnpj(),
            email=self._faker.company_email(),
            phone_number=self._faker.phone_number(),
        )
