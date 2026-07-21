from random import choices

from simulator.domain.reviews.review_model import Review


class ReviewGenerator:
    _RATINGS = (5, 4, 3, 2, 1)

    _WEIGHTS = (
        65,
        20,
        8,
        4,
        3,
    )

    _COMMENTS = {
        5: (
            "Excelente produto",
            "Entrega rápida e produto excelente.",
        ),
        4: (
            "Muito bom",
            "Produto muito bom e chegou no prazo.",
        ),
        3: (
            "Bom",
            "Atendeu às expectativas.",
        ),
        2: (
            "Poderia ser melhor",
            "Produto diferente do esperado.",
        ),
        1: (
            "Muito ruim",
            "Produto apresentou problemas.",
        ),
    }

    def generate(
        self,
        order_id,
        customer_id,
        product_id,
    ) -> Review:

        rating = choices(
            self._RATINGS,
            weights=self._WEIGHTS,
            k=1,
        )[0]

        title, comment = self._COMMENTS[rating]

        return Review.create(
            order_id=order_id,
            customer_id=customer_id,
            product_id=product_id,
            rating=rating,
            title=title,
            comment=comment,
        )
