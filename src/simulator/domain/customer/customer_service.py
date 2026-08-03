from psycopg import Connection

from simulator.core.batch_writer import BatchWriter
from simulator.core.reference_pool import ReferencePool
from simulator.core.unique_insert import insert_with_unique_retry
from simulator.domain.customer.address_generator import CustomerAddressGenerator
from simulator.domain.customer.address_repository import CustomerAddressRepository
from simulator.domain.customer.customer_generator import CustomerGenerator
from simulator.domain.customer.customer_model import Customer
from simulator.domain.customer.customer_repository import CustomerRepository


class CustomerService:
    def __init__(self) -> None:
        self._customer_generator = CustomerGenerator()
        self._address_generator = CustomerAddressGenerator()

    def create_customer(
        self,
        connection: Connection,
        writer: BatchWriter,
        pool: ReferencePool,
    ) -> Customer:
        customer_repository = CustomerRepository(connection)
        address_repository = CustomerAddressRepository(writer)

        customer = insert_with_unique_retry(
            "customer",
            self._customer_generator.generate,
            customer_repository.insert,
        )

        pool.customer_ids.append(customer.customer_id)

        address = self._address_generator.generate(customer.customer_id)
        address_repository.insert(address)

        return customer
