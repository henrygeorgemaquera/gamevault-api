from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ClassificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None


class GameRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    developer: str
    publisher: str
    release_date: Optional[date] = None
    price: float
    discount_percent: int
    offer_start_date: Optional[datetime] = None
    offer_end_date: Optional[datetime] = None
    # Campos calculados automáticamente según la vigencia de la oferta
    is_on_sale: bool
    effective_discount_percent: int
    final_price: float
    image_url: Optional[str] = None
    classifications: List[ClassificationRead] = []


class PaginatedGamesResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[GameRead]
