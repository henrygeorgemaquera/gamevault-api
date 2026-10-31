from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import Depends
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.config.database import get_db
from app.models.catalog import Classification, Game
from app.models.order import Order, OrderItem
from app.models.user import User
from app.models.wishlist import WishlistItem
from app.schemas.admin import MostPurchasedGameItem, MostWishedGameItem


class IAdminRepository(ABC):
    # Clasificaciones
    @abstractmethod
    def list_classifications(
        self, include_inactive: bool = True
    ) -> List[Classification]: ...

    @abstractmethod
    def get_classification_by_id(
        self, classification_id: int
    ) -> Optional[Classification]: ...

    @abstractmethod
    def get_classification_by_name(
        self, name: str
    ) -> Optional[Classification]: ...

    @abstractmethod
    def get_classifications_by_ids(
        self, ids: List[int]
    ) -> List[Classification]: ...

    @abstractmethod
    def save_classification(
        self, classification: Classification
    ) -> Classification: ...

    # Juegos
    @abstractmethod
    def list_games(
        self,
        include_inactive: bool = True,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Game], int]: ...

    @abstractmethod
    def get_game_by_id(self, game_id: int) -> Optional[Game]: ...

    @abstractmethod
    def get_game_by_title(self, title: str) -> Optional[Game]: ...

    @abstractmethod
    def save_game(self, game: Game) -> Game: ...

    # Usuarios
    @abstractmethod
    def list_users(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[User], int]: ...

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    def save_user(self, user: User) -> User: ...

    # Reportes de popularidad
    @abstractmethod
    def get_most_purchased_games(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[MostPurchasedGameItem]: ...

    @abstractmethod
    def get_most_wished_games(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[MostWishedGameItem]: ...


class AdminRepository(IAdminRepository):
    def __init__(self, db: Session):
        self.db = db

    # --- Clasificaciones ---
    def list_classifications(
        self, include_inactive: bool = True
    ) -> List[Classification]:
        stmt = select(Classification)
        if not include_inactive:
            stmt = stmt.where(col(Classification.is_active).is_(True))
        stmt = stmt.order_by(col(Classification.name).asc())
        return list(self.db.exec(stmt).all())

    def get_classification_by_id(
        self, classification_id: int
    ) -> Optional[Classification]:
        return self.db.get(Classification, classification_id)

    def get_classification_by_name(self, name: str) -> Optional[Classification]:
        stmt = select(Classification).where(
            func.lower(col(Classification.name)) == name.strip().lower()
        )
        return self.db.exec(stmt).first()

    def get_classifications_by_ids(
        self, ids: List[int]
    ) -> List[Classification]:
        if not ids:
            return []
        stmt = select(Classification).where(col(Classification.id).in_(ids))
        return list(self.db.exec(stmt).all())

    def save_classification(
        self, classification: Classification
    ) -> Classification:
        self.db.add(classification)
        self.db.commit()
        self.db.refresh(classification)
        return classification

    # --- Juegos ---
    def list_games(
        self,
        include_inactive: bool = True,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Game], int]:
        stmt = select(Game)
        if not include_inactive:
            stmt = stmt.where(col(Game.is_active).is_(True))
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(col(Game.title).ilike(pattern))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.exec(count_stmt).one()

        offset = (page - 1) * page_size
        stmt = (
            stmt.order_by(col(Game.created_at).desc())
            .offset(offset)
            .limit(page_size)
        )
        games = list(self.db.exec(stmt).all())
        return games, total

    def get_game_by_id(self, game_id: int) -> Optional[Game]:
        return self.db.get(Game, game_id)

    def get_game_by_title(self, title: str) -> Optional[Game]:
        stmt = select(Game).where(
            func.lower(col(Game.title)) == title.strip().lower()
        )
        return self.db.exec(stmt).first()

    def save_game(self, game: Game) -> Game:
        self.db.add(game)
        self.db.commit()
        self.db.refresh(game)
        return game

    # --- Usuarios ---
    def list_users(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[User], int]:
        stmt = select(User)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(col(User.email).ilike(pattern))
        if role is not None:
            stmt = stmt.where(col(User.role) == role)
        if is_active is not None:
            stmt = stmt.where(col(User.is_active).is_(is_active))
        if is_verified is not None:
            stmt = stmt.where(col(User.is_verified).is_(is_verified))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.exec(count_stmt).one()

        offset = (page - 1) * page_size
        stmt = (
            stmt.order_by(col(User.created_at).desc())
            .offset(offset)
            .limit(page_size)
        )
        users = list(self.db.exec(stmt).all())
        return users, total

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.get(User, user_id)

    def save_user(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    # --- Reportes de Popularidad en un Período ---
    def get_most_purchased_games(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[MostPurchasedGameItem]:
        stmt = (
            select(
                col(Game.id),
                col(Game.title),
                col(Game.is_active),
                func.count(col(OrderItem.id)).label("purchase_count"),
                func.coalesce(func.sum(col(OrderItem.final_price_snapshot)), 0.0).label(
                    "total_revenue"
                ),
            )
            .join(OrderItem, col(OrderItem.game_id) == col(Game.id))
            .join(Order, col(Order.id) == col(OrderItem.order_id))
            .where(col(Order.status) == "completed")
        )

        if start_date is not None:
            stmt = stmt.where(col(Order.created_at) >= start_date)
        if end_date is not None:
            stmt = stmt.where(col(Order.created_at) <= end_date)

        stmt = (
            stmt.group_by(col(Game.id), col(Game.title), col(Game.is_active))
            .order_by(
                func.count(col(OrderItem.id)).desc(),
                func.sum(col(OrderItem.final_price_snapshot)).desc(),
            )
            .limit(limit)
        )

        rows = self.db.exec(stmt).all()
        return [
            MostPurchasedGameItem(
                game_id=row[0],
                title=row[1],
                is_active=row[2],
                purchase_count=int(row[3]),
                total_revenue=round(float(row[4]), 2),
            )
            for row in rows
        ]

    def get_most_wished_games(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[MostWishedGameItem]:
        stmt = (
            select(
                col(Game.id),
                col(Game.title),
                col(Game.is_active),
                func.count(col(WishlistItem.id)).label("wishlist_count"),
            )
            .join(WishlistItem, col(WishlistItem.game_id) == col(Game.id))
        )

        if start_date is not None:
            stmt = stmt.where(col(WishlistItem.created_at) >= start_date)
        if end_date is not None:
            stmt = stmt.where(col(WishlistItem.created_at) <= end_date)

        stmt = (
            stmt.group_by(col(Game.id), col(Game.title), col(Game.is_active))
            .order_by(func.count(col(WishlistItem.id)).desc())
            .limit(limit)
        )

        rows = self.db.exec(stmt).all()
        return [
            MostWishedGameItem(
                game_id=row[0],
                title=row[1],
                is_active=row[2],
                wishlist_count=int(row[3]),
            )
            for row in rows
        ]


def get_admin_repository(db: Session = Depends(get_db)) -> IAdminRepository:
    return AdminRepository(db)
