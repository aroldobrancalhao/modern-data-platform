from simulator.core.database import Database

from simulator.domain.orders.order_repository import OrderRepository
from simulator.domain.reviews.review_generator import ReviewGenerator
from simulator.domain.reviews.review_model import Review
from simulator.domain.reviews.review_repository import ReviewRepository


class ReviewService:

    def __init__(self) -> None:
        self._database = Database()
        self._generator = ReviewGenerator()

    def create_review(self) -> Review:

        with self._database.connection() as connection:

            order_repository = OrderRepository(connection)

            order = order_repository.get_random_order()

            if order is None:
                raise ValueError("No order found.")

            (
                order_id,
                customer_id,
                product_id,
                _,
            ) = order

            review = self._generator.generate(
                order_id=order_id,
                customer_id=customer_id,
                product_id=product_id,
            )

            repository = ReviewRepository(connection)

            repository.create_review(review)

            return review