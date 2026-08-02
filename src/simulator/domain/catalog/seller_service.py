from psycopg import Connection

from simulator.domain.catalog.seller_generator import SellerGenerator
from simulator.domain.catalog.seller_model import Seller
from simulator.domain.catalog.seller_repository import SellerRepository


class SellerService:
    def __init__(self) -> None:
        self._generator = SellerGenerator()

    def create_seller(self, connection: Connection) -> Seller:
        repository = SellerRepository(connection)

        while True:
            seller = self._generator.generate()

            if repository.insert(seller):
                return seller
