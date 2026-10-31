import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import Depends, HTTPException, status

from app.models.catalog import Game
from app.repositories.catalog_repository import (
    ICatalogRepository,
    get_catalog_repository,
)
from app.schemas.catalog import (
    ClassificationRead,
    GameRead,
    PaginatedGamesResponse,
)
from app.utils.security import utcnow


def _normalize_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Asegura que la fecha leída de SQLite tenga zona horaria UTC para compararla."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def calculate_game_pricing(
    game: Game, now: Optional[datetime] = None
) -> Tuple[bool, int, float]:
    """
    Evalúa si el juego tiene una oferta vigente en el instante `now`.
    Retorna: (is_on_sale, effective_discount_percent, final_price).
    """
    current_time = now or utcnow()
    if game.discount_percent <= 0:
        return False, 0, round(game.price, 2)

    start = _normalize_utc(game.offer_start_date)
    end = _normalize_utc(game.offer_end_date)

    if start and current_time < start:
        return False, 0, round(game.price, 2)
    if end and current_time > end:
        return False, 0, round(game.price, 2)

    final_price = round(game.price * (1 - game.discount_percent / 100.0), 2)
    return True, game.discount_percent, final_price


def to_game_read(game: Game, now: Optional[datetime] = None) -> GameRead:
    is_on_sale, effective_discount, final_price = calculate_game_pricing(game, now)
    active_classifications = [
        ClassificationRead.model_validate(c)
        for c in game.classifications
        if c.is_active
    ]
    return GameRead(
        id=game.id,
        title=game.title,
        description=game.description,
        developer=game.developer,
        publisher=game.publisher,
        release_date=game.release_date,
        price=game.price,
        discount_percent=game.discount_percent,
        offer_start_date=game.offer_start_date,
        offer_end_date=game.offer_end_date,
        is_on_sale=is_on_sale,
        effective_discount_percent=effective_discount,
        final_price=final_price,
        image_url=game.image_url,
        classifications=active_classifications,
    )


class CatalogService:
    def __init__(
        self,
        catalog_repo: ICatalogRepository = Depends(get_catalog_repository),
    ):
        self.catalog_repo = catalog_repo

    def list_games(
        self,
        search: Optional[str] = None,
        classification_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        on_sale: Optional[bool] = None,
        sort_by: str = "title",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedGamesResponse:
        if (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "El precio mínimo no puede ser mayor que el precio máximo",
            )

        now = utcnow()
        games, total = self.catalog_repo.list_public_games(
            now=now,
            search=search,
            classification_id=classification_id,
            min_price=min_price,
            max_price=max_price,
            on_sale=on_sale,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )

        items = [to_game_read(game, now) for game in games]
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedGamesResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=items,
        )

    def get_game_detail(self, game_id: int) -> GameRead:
        game = self.catalog_repo.get_active_game_by_id(game_id)
        if game is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "El título solicitado no existe o no se encuentra disponible",
            )
        return to_game_read(game, utcnow())

    def list_classifications(self) -> List[ClassificationRead]:
        classifications = self.catalog_repo.list_active_classifications()
        return [ClassificationRead.model_validate(c) for c in classifications]
