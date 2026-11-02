from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    # Clave de idempotencia para evitar compras duplicadas
    idempotency_key: str = Field(unique=True, index=True, max_length=100)
    total_amount: float = Field(ge=0)
    status: str = Field(default="completed", max_length=30, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    # Fecha en que se envió la boleta por correo; evita enviarla dos veces
    receipt_sent_at: Optional[datetime] = Field(default=None)

    items: List["OrderItem"] = Relationship(back_populates="order")


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    game_id: int = Field(foreign_key="games.id", index=True)

    # Detalle estático del pedido para conservar trazabilidad histórica
    game_title_snapshot: str = Field(max_length=200)
    unit_price_snapshot: float = Field(ge=0)
    discount_percent_snapshot: int = Field(default=0, ge=0, le=100)
    final_price_snapshot: float = Field(ge=0)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )

    order: Optional[Order] = Relationship(back_populates="items")
