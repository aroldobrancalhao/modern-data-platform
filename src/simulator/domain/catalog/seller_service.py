from simulator.core.database import Database

from simulator.domain.catalog.seller_generator import SellerGenerator
from simulator.domain.catalog.seller_model import Seller
from simulator.domain.catalog.seller_repository import SellerRepository


class SellerService:
    def __init__(self) -> None:
        self._database = Database()
        self._generator = SellerGenerator()

    def create_seller(self) -> Seller:
        with self._database.connection() as connection:
            repository = SellerRepository(connection)

            while True:
                seller = self._generator.generate()

                if repository.insert(seller):
                    return seller
