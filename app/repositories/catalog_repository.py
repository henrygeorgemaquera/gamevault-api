from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import Depends
from sqlalchemy import case, func, or_
from sqlmodel import Session, col, select

from app.config.database import get_db
from app.models.catalog import Classification, Game, GameClassificationLink


# EL CONTRATO
class ICatalogRepository(ABC):
    @abstractmethod
    def list_public_games(
        self,
        now: datetime,
        search: Optional[str] = None,
        classification_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        on_sale: Optional[bool] = None,
        sort_by: str = "title",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Game], int]: ...

    @abstractmethod
    def get_active_game_by_id(self, game_id: int) -> Optional[Game]: ...

    @abstractmethod
    def list_active_classifications(self) -> List[Classification]: ...


# LA IMPLEMENTACIÓN con SQLModel
class CatalogRepository(ICatalogRepository):
    def __init__(self, db: Session):
        self.db = db

    def list_public_games(
        self,
        now: datetime,
        search: Optional[str] = None,
        classification_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        on_sale: Optional[bool] = None,
        sort_by: str = "title",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Game], int]:
        # Solo títulos activos (soft delete respetado)
        statement = select(Game).where(col(Game.is_active).is_(True))

        # Búsqueda textual en título, descripción o desarrollador
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    col(Game.title).ilike(pattern),
                    col(Game.description).ilike(pattern),
                    col(Game.developer).ilike(pattern),
                )
            )

        # Filtro por clasificación activa
        if classification_id is not None:
            statement = (
                statement.join(
                    GameClassificationLink,
                    col(GameClassificationLink.game_id) == col(Game.id),
                )
                .join(
                    Classification,
                    col(Classification.id)
                    == col(GameClassificationLink.classification_id),
                )
                .where(
                    col(Classification.id) == classification_id,
                    col(Classification.is_active).is_(True),
                )
            )

        # Condición SQL de oferta vigente en la fecha actual
        sale_condition = (
            (col(Game.discount_percent) > 0)
            & (
                col(Game.offer_start_date).is_(None)
                | (col(Game.offer_start_date) <= now)
            )
            & (
                col(Game.offer_end_date).is_(None)
                | (col(Game.offer_end_date) >= now)
            )
        )

        # Precio efectivo (aplica el descuento en SQL solo si la oferta está vigente)
        effective_price = case(
            (
                sale_condition,
                col(Game.price) * (100 - col(Game.discount_percent)) / 100.0,
            ),
            else_=col(Game.price),
        )

        # Filtros por rango de precio efectivo
        if min_price is not None:
            statement = statement.where(effective_price >= min_price)
        if max_price is not None:
            statement = statement.where(effective_price <= max_price)

        # Filtro de oferta vigente
        if on_sale is True:
            statement = statement.where(sale_condition)
        elif on_sale is False:
            statement = statement.where(~sale_condition)

        # Conteo total antes de paginar
        count_stmt = select(func.count()).select_from(statement.subquery())
        total = self.db.exec(count_stmt).one()

        # Ordenamiento (ordenar por price usa el precio final vigente)
        sort_map = {
            "title": col(Game.title),
            "price": effective_price,
            "release_date": col(Game.release_date),
            "created_at": col(Game.created_at),
        }
        sort_col = sort_map.get(sort_by, col(Game.title))
        if sort_order.lower() == "desc":
            statement = statement.order_by(sort_col.desc())
        else:
            statement = statement.order_by(sort_col.asc())

        # Paginación
        offset = (page - 1) * page_size
        statement = statement.offset(offset).limit(page_size)
        games = list(self.db.exec(statement).all())

        return games, total

    def get_active_game_by_id(self, game_id: int) -> Optional[Game]:
        statement = select(Game).where(
            col(Game.id) == game_id, col(Game.is_active).is_(True)
        )
        return self.db.exec(statement).first()

    def list_active_classifications(self) -> List[Classification]:
        statement = (
            select(Classification)
            .where(col(Classification.is_active).is_(True))
            .order_by(col(Classification.name).asc())
        )
        return list(self.db.exec(statement).all())


def get_catalog_repository(
    db: Session = Depends(get_db),
) -> ICatalogRepository:
    return CatalogRepository(db)
