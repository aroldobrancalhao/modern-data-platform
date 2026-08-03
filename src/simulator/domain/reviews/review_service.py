from simulator.core.batch_writer import BatchWriter
from simulator.core.reference_pool import ReferencePool
from simulator.domain.reviews.review_generator import ReviewGenerator
from simulator.domain.reviews.review_model import Review
from simulator.domain.reviews.review_repository import ReviewRepository


class ReviewService:
    def __init__(self) -> None:
        self._generator = ReviewGenerator()

    def create_review(self, writer: BatchWriter, pool: ReferencePool) -> Review:
        order = pool.random_order()

        if order is None:
            raise ValueError("No order found.")

        review = self._generator.generate(
            order_id=order.order_id,
            customer_id=order.customer_id,
            product_id=order.product_id,
        )

        repository = ReviewRepository(writer)

        repository.create_review(review)

        return review
