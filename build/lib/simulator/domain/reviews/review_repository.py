from psycopg import Connection

from simulator.domain.reviews.review_model import Review


class ReviewRepository:

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def create_review(
        self,
        review: Review,
    ) -> None:

        with self._connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO marketplace.reviews
                (
                    review_id,
                    order_id,
                    customer_id,
                    product_id,
                    rating,
                    title,
                    comment,
                    created_at,
                    updated_at
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                ON CONFLICT (order_id, product_id)
                DO NOTHING
                RETURNING review_id
                """,
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

        self._connection.commit()