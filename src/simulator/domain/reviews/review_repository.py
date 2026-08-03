from simulator.core.batch_writer import BatchWriter
from simulator.domain.reviews.review_model import Review


class ReviewRepository:
    def __init__(self, writer: BatchWriter) -> None:
        self._writer = writer

    def create_review(
        self,
        review: Review,
    ) -> None:
        self._writer.add(
            "marketplace.reviews",
            (
                "review_id",
                "order_id",
                "customer_id",
                "product_id",
                "rating",
                "title",
                "comment",
                "created_at",
                "updated_at",
            ),
            (
                review.review_id,
                review.order_id,
                review.customer_id,
                review.product_id,
                review.rating,
                review.title,
                review.comment,
                review.created_at,
                review.updated_at,
            ),
        )
