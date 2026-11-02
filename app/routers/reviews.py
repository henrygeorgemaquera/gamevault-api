from typing import List

from fastapi import APIRouter, Depends, status

from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewRead
from app.services.review_service import ReviewService
from app.utils.security import get_current_user

router = APIRouter(prefix="/games", tags=["Reseñas"])


# Requiere sesión; solo para títulos que el usuario ya compró
@router.post(
    "/{game_id}/reviews",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    game_id: int,
    data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(),
):
    return service.create_review(current_user, game_id, data)


# Pública: cualquiera puede ver las reseñas de un título
@router.get("/{game_id}/reviews", response_model=List[ReviewRead])
def list_reviews(game_id: int, service: ReviewService = Depends()):
    return service.list_reviews(game_id)
