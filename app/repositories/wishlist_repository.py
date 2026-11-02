from abc import ABC, abstractmethod
from typing import List, Tuple

from fastapi import Depends
from sqlmodel import Session, col, select

from app.config.database import get_db
from app.models.catalog import Game
from app.models.wishlist import WishlistItem


# 1. EL CONTRATO: lo que el service puede pedirle al repositorio
class IWishlistRepository(ABC):
    @abstractmethod
    def list_by_user(self, user_id: int) -> List[Tuple[WishlistItem, Game]]: ...

    @abstractmethod
    def exists(self, user_id: int, game_id: int) -> bool: ...

    @abstractmethod
    def add(self, user_id: int, game_id: int) -> WishlistItem: ...

    @abstractmethod
    def remove(self, user_id: int, game_id: int) -> bool: ...


# 2. LA IMPLEMENTACIÓN con SQLModel
class WishlistRepository(IWishlistRepository):
    def __init__(self, db: Session):
        self.db = db

    # Deseados del usuario con los datos del juego; los retirados del catálogo no se muestran
    def list_by_user(self, user_id: int) -> List[Tuple[WishlistItem, Game]]:
        statement = (
            select(WishlistItem, Game)
            .join(Game, col(Game.id) == col(WishlistItem.game_id))
            .where(col(WishlistItem.user_id) == user_id, col(Game.is_active).is_(True))
            .order_by(col(WishlistItem.created_at).desc(), col(WishlistItem.id).desc())
        )
        return list(self.db.exec(statement).all())

    def exists(self, user_id: int, game_id: int) -> bool:
        statement = select(WishlistItem.id).where(
            col(WishlistItem.user_id) == user_id, col(WishlistItem.game_id) == game_id
        )
        return self.db.exec(statement).first() is not None

    def add(self, user_id: int, game_id: int) -> WishlistItem:
        item = WishlistItem(user_id=user_id, game_id=game_id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove(self, user_id: int, game_id: int) -> bool:
        statement = select(WishlistItem).where(
            col(WishlistItem.user_id) == user_id, col(WishlistItem.game_id) == game_id
        )
        item = self.db.exec(statement).first()
        if item is None:
            return False
        self.db.delete(item)
        self.db.commit()
        return True


# Aquí se elige la implementación concreta que recibe el service
def get_wishlist_repository(db: Session = Depends(get_db)) -> IWishlistRepository:
    return WishlistRepository(db)
