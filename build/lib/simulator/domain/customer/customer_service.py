from simulator.core.database import Database
from simulator.domain.customer.address_generator import CustomerAddressGenerator
from simulator.domain.customer.address_model import CustomerAddress
from simulator.domain.customer.address_repository import CustomerAddressRepository
from simulator.domain.customer.customer_generator import CustomerGenerator
from simulator.domain.customer.customer_model import Customer
from simulator.domain.customer.customer_repository import CustomerRepository


class CustomerService:
    def __init__(self) -> None:
        self._database = Database()
        self._customer_generator = CustomerGenerator()
        self._address_generator = CustomerAddressGenerator()

    def create_customer(self) -> Customer:
        with self._database.connection() as connection:
            customer_repository = CustomerRepository(connection)
            address_repository = CustomerAddressRepository(connection)

            while True:
                customer = self._customer_generator.generate()

                if customer_repository.insert(customer):
                    break

            address = self._address_generator.generate(customer.customer_id)
            address_repository.insert(address)

        return customer