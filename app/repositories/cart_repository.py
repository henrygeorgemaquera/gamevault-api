from abc import ABC, abstractmethod
from typing import List, Optional

from fastapi import Depends
from sqlmodel import Session, col, select

from app.config.database import get_db
from app.models.cart import Cart, CartItem


# 1. EL CONTRATO: lo que el service puede pedirle al repositorio
class ICartRepository(ABC):
    @abstractmethod
    def get_by_user_id(self, user_id: int) -> Optional[Cart]: ...

    @abstractmethod
    def get_by_guest_token(self, guest_token: str) -> Optional[Cart]: ...

    @abstractmethod
    def create(
        self, user_id: Optional[int] = None, guest_token: Optional[str] = None
    ) -> Cart: ...

    @abstractmethod
    def list_items(self, cart_id: int) -> List[CartItem]: ...

    @abstractmethod
    def has_item(self, cart_id: int, game_id: int) -> bool: ...

    @abstractmethod
    def add_items(self, cart_id: int, game_ids: List[int]) -> None: ...

    @abstractmethod
    def remove_item(self, cart_id: int, game_id: int) -> bool: ...

    @abstractmethod
    def delete_cart(self, cart: Cart) -> None: ...


# 2. LA IMPLEMENTACIÓN con SQLModel
class CartRepository(ICartRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: int) -> Optional[Cart]:
        statement = select(Cart).where(col(Cart.user_id) == user_id)
        return self.db.exec(statement).first()

    def get_by_guest_token(self, guest_token: str) -> Optional[Cart]:
        statement = select(Cart).where(col(Cart.guest_token) == guest_token)
        return self.db.exec(statement).first()

    def create(
        self, user_id: Optional[int] = None, guest_token: Optional[str] = None
    ) -> Cart:
        cart = Cart(user_id=user_id, guest_token=guest_token)
        self.db.add(cart)
        self.db.commit()
        self.db.refresh(cart)
        return cart

    def list_items(self, cart_id: int) -> List[CartItem]:
        statement = (
            select(CartItem)
            .where(col(CartItem.cart_id) == cart_id)
            .order_by(col(CartItem.added_at).asc(), col(CartItem.id).asc())
        )
        return list(self.db.exec(statement).all())

    def has_item(self, cart_id: int, game_id: int) -> bool:
        statement = select(CartItem.id).where(
            col(CartItem.cart_id) == cart_id, col(CartItem.game_id) == game_id
        )
        return self.db.exec(statement).first() is not None

    # Agrega varios títulos con un solo commit (también sirve para uno)
    def add_items(self, cart_id: int, game_ids: List[int]) -> None:
        self.db.add_all([CartItem(cart_id=cart_id, game_id=gid) for gid in game_ids])
        self.db.commit()

    def remove_item(self, cart_id: int, game_id: int) -> bool:
        statement = select(CartItem).where(
            col(CartItem.cart_id) == cart_id, col(CartItem.game_id) == game_id
        )
        item = self.db.exec(statement).first()
        if item is None:
            return False
        self.db.delete(item)
        self.db.commit()
        return True

    # Borra el carrito y, por cascada, sus ítems
    def delete_cart(self, cart: Cart) -> None:
        self.db.delete(cart)
        self.db.commit()


# Aquí se elige la implementación concreta que recibe el service
def get_cart_repository(db: Session = Depends(get_db)) -> ICartRepository:
    return CartRepository(db)
