from typing import List

from fastapi import APIRouter, Depends, status

from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.wishlist import AddToWishlistRequest, WishlistItemRead
from app.services.wishlist_service import WishlistService
from app.utils.security import get_current_user

# Todas las rutas requieren sesión: la lista de deseados es personal
router = APIRouter(prefix="/wishlist", tags=["Lista de deseados"])


@router.get("", response_model=List[WishlistItemRead])
def list_wishlist(
    current_user: User = Depends(get_current_user),
    service: WishlistService = Depends(),
):
    return service.list_items(current_user)


@router.post("", response_model=WishlistItemRead, status_code=status.HTTP_201_CREATED)
def add_to_wishlist(
    data: AddToWishlistRequest,
    current_user: User = Depends(get_current_user),
    service: WishlistService = Depends(),
):
    return service.add_item(current_user, data.game_id)


@router.delete("/{game_id}", response_model=MessageResponse)
def remove_from_wishlist(
    game_id: int,
    current_user: User = Depends(get_current_user),
    service: WishlistService = Depends(),
):
    return MessageResponse(message=service.remove_item(current_user, game_id))
