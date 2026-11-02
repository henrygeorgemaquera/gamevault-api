from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.models.catalog import Game


# Carrito de un usuario registrado (user_id) o de un invitado (guest_token)
class Cart(SQLModel, table=True):
    __tablename__ = "carts"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Un usuario tiene un solo carrito; en los de invitado user_id queda vacío
    user_id: Optional[int] = Field(
        default=None, foreign_key="users.id", unique=True, index=True
    )
    # Identifica al carrito de un invitado (viaja en el header X-Cart-Token)
    guest_token: Optional[str] = Field(
        default=None, unique=True, index=True, max_length=64
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )

    items: List["CartItem"] = Relationship(
        back_populates="cart",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class CartItem(SQLModel, table=True):
    __tablename__ = "cart_items"
    # Un título no puede repetirse dentro del mismo carrito (son juegos digitales)
    __table_args__ = (UniqueConstraint("cart_id", "game_id", name="uq_cart_game"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    cart_id: int = Field(foreign_key="carts.id", index=True)
    game_id: int = Field(foreign_key="games.id", index=True)
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    cart: Optional[Cart] = Relationship(back_populates="items")
    game: Optional[Game] = Relationship()
