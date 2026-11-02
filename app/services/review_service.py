import logging
from typing import List

from fastapi import Depends, HTTPException, status

from app.models.review import Review
from app.models.user import User
from app.repositories.catalog_repository import (
    ICatalogRepository,
    get_catalog_repository,
)
from app.repositories.order_repository import IOrderRepository, get_order_repository
from app.repositories.review_repository import (
    IReviewRepository,
    get_review_repository,
)
from app.schemas.review import ReviewCreate, ReviewRead

logger = logging.getLogger(__name__)


class ReviewService:
    def __init__(
        self,
        review_repo: IReviewRepository = Depends(get_review_repository),
        order_repo: IOrderRepository = Depends(get_order_repository),
        catalog_repo: ICatalogRepository = Depends(get_catalog_repository),
    ):
        self.review_repo = review_repo
        self.order_repo = order_repo
        self.catalog_repo = catalog_repo

    def create_review(
        self, user: User, game_id: int, data: ReviewCreate
    ) -> ReviewRead:
        # Solo se puede reseñar un título de la biblioteca (ya comprado)
        if game_id not in self.order_repo.get_owned_game_ids(user.id):
            logger.warning(
                "Reseña denegada, título fuera de la biblioteca: user_id=%s, game_id=%s",
                user.id,
                game_id,
            )
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Solo puedes reseñar títulos de tu biblioteca",
            )

        # Una sola reseña por título
        if self.review_repo.exists_for_user(user.id, game_id):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Ya reseñaste este título"
            )

        review = Review(
            user_id=user.id,
            game_id=game_id,
            rating=data.rating,
            comment=data.comment,
        )
        saved = self.review_repo.create(review)
        logger.info(
            "Reseña creada: review_id=%s, user_id=%s, game_id=%s",
            saved.id,
            user.id,
            game_id,
        )
        return ReviewRead.model_validate(saved)

    def list_reviews(self, game_id: int) -> List[ReviewRead]:
        if self.catalog_repo.get_active_game_by_id(game_id) is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Título no encontrado o no disponible"
            )
        return [
            ReviewRead.model_validate(r) for r in self.review_repo.list_by_game(game_id)
        ]
