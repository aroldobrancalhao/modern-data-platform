from simulator.core.database import Database
from simulator.domain.catalog.seller_generator import SellerGenerator
from simulator.domain.catalog.seller_model import Seller
from simulator.domain.catalog.seller_repository import SellerRepository


class SellerService:
    def __init__(self) -> None:
        self._database = Database()
        self._generator = SellerGenerator()

    def create_seller(self) -> Seller:
        seller = self._generator.generate()

        with self._database.connection() as connection:
            repository = SellerRepository(connection)
            repository.insert(seller)

        return seller