from simulator.core.database import Database
from simulator.domain.customer.generator import CustomerGenerator
from simulator.domain.customer.model import Customer
from simulator.domain.customer.repository import CustomerRepository


class CustomerService:
    def __init__(self) -> None:
        self._database = Database()
        self._generator = CustomerGenerator()

    def create_customer(self) -> Customer:
        customer = self._generator.generate()

        with self._database.connection() as connection:
            repository = CustomerRepository(connection)
            repository.insert(customer)

        return customer