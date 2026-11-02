import logging
from typing import List

from fastapi import Depends, HTTPException, status

from app.models.catalog import Game
from app.models.user import User
from app.models.wishlist import WishlistItem
from app.repositories.catalog_repository import (
    ICatalogRepository,
    get_catalog_repository,
)
from app.repositories.wishlist_repository import (
    IWishlistRepository,
    get_wishlist_repository,
)
from app.schemas.wishlist import WishlistItemRead
from app.services.catalog_service import calculate_game_pricing

logger = logging.getLogger(__name__)


def to_wishlist_item_read(item: WishlistItem, game: Game) -> WishlistItemRead:
    _, _, final_price = calculate_game_pricing(game)
    return WishlistItemRead(
        game_id=game.id,
        title=game.title,
        image_url=game.image_url,
        price=game.price,
        final_price=final_price,
        added_at=item.created_at,
    )


class WishlistService:
    def __init__(
        self,
        wishlist_repo: IWishlistRepository = Depends(get_wishlist_repository),
        catalog_repo: ICatalogRepository = Depends(get_catalog_repository),
    ):
        self.wishlist_repo = wishlist_repo
        self.catalog_repo = catalog_repo

    def list_items(self, user: User) -> List[WishlistItemRead]:
        return [
            to_wishlist_item_read(item, game)
            for item, game in self.wishlist_repo.list_by_user(user.id)
        ]

    def add_item(self, user: User, game_id: int) -> WishlistItemRead:
        game = self.catalog_repo.get_active_game_by_id(game_id)
        if game is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Título no encontrado o no disponible"
            )
        if self.wishlist_repo.exists(user.id, game_id):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "El título ya está en tu lista de deseados",
            )
        item = self.wishlist_repo.add(user.id, game_id)
        logger.info("Título agregado a deseados: user_id=%s, game_id=%s", user.id, game_id)
        return to_wishlist_item_read(item, game)

    def remove_item(self, user: User, game_id: int) -> str:
        if not self.wishlist_repo.remove(user.id, game_id):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "El título no está en tu lista de deseados",
            )
        logger.info("Título quitado de deseados: user_id=%s, game_id=%s", user.id, game_id)
        return "Título quitado de tu lista de deseados"
