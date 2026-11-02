from datetime import datetime
from typing import List

from pydantic import BaseModel


class OrderItemRead(BaseModel):
    game_id: int
    # Datos congelados al momento de la compra (no cambian si el juego se edita)
    title: str
    unit_price: float
    discount_percent: int
    final_price: float


class OrderRead(BaseModel):
    id: int
    status: str
    total_amount: float
    created_at: datetime
    items: List[OrderItemRead]


# Versión corta para el historial: sin el detalle de cada título
class OrderSummaryRead(BaseModel):
    id: int
    status: str
    total_amount: float
    created_at: datetime
    item_count: int
