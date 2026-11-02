from abc import ABC, abstractmethod
from typing import List

from fastapi import Depends
from sqlmodel import Session, col, select

from app.config.database import get_db
from app.models.review import Review


# 1. EL CONTRATO: lo que el service puede pedirle al repositorio
class IReviewRepository(ABC):
    @abstractmethod
    def exists_for_user(self, user_id: int, game_id: int) -> bool: ...

    @abstractmethod
    def create(self, review: Review) -> Review: ...

    @abstractmethod
    def list_by_game(self, game_id: int) -> List[Review]: ...


# 2. LA IMPLEMENTACIÓN con SQLModel
class ReviewRepository(IReviewRepository):
    def __init__(self, db: Session):
        self.db = db

    def exists_for_user(self, user_id: int, game_id: int) -> bool:
        statement = select(Review.id).where(
            col(Review.user_id) == user_id, col(Review.game_id) == game_id
        )
        return self.db.exec(statement).first() is not None

    def create(self, review: Review) -> Review:
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    # Reseñas de un título, las más recientes primero
    def list_by_game(self, game_id: int) -> List[Review]:
        statement = (
            select(Review)
            .where(col(Review.game_id) == game_id)
            .order_by(col(Review.created_at).desc(), col(Review.id).desc())
        )
        return list(self.db.exec(statement).all())


# Aquí se elige la implementación concreta que recibe el service
def get_review_repository(db: Session = Depends(get_db)) -> IReviewRepository:
    return ReviewRepository(db)
