from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AddToWishlistRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"game_id": 1}})

    game_id: int = Field(gt=0, description="ID del título que se agrega a deseados")


class WishlistItemRead(BaseModel):
    game_id: int
    title: str
    image_url: Optional[str] = None
    price: float
    # Precio actual con la oferta vigente (si la hay)
    final_price: float
    added_at: datetime
