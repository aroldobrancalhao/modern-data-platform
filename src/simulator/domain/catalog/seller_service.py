from psycopg import Connection

from simulator.core.reference_pool import ReferencePool
from simulator.core.unique_insert import insert_with_unique_retry
from simulator.domain.catalog.seller_generator import SellerGenerator
from simulator.domain.catalog.seller_model import Seller
from simulator.domain.catalog.seller_repository import SellerRepository


class SellerService:
    def __init__(self) -> None:
        self._generator = SellerGenerator()

    def create_seller(self, connection: Connection, pool: ReferencePool) -> Seller:
        repository = SellerRepository(connection)

        seller = insert_with_unique_retry(
            "seller",
            self._generator.generate,
            repository.insert,
        )

        pool.seller_ids.append(seller.seller_id)

        return seller
