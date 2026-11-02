from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"rating": 5, "comment": "Excelente juego"}}
    )

    rating: int = Field(ge=1, le=5, description="Valoración de 1 a 5")
    comment: str = Field(min_length=3, max_length=1000, description="Comentario")


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    game_id: int
    user_id: int
    rating: int
    comment: str
    created_at: datetime
