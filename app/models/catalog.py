from datetime import date, datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


# Tabla intermedia N:M entre Juegos y Clasificaciones (Géneros / Categorías)
class GameClassificationLink(SQLModel, table=True):
    __tablename__ = "game_classifications"

    game_id: Optional[int] = Field(
        default=None, foreign_key="games.id", primary_key=True
    )
    classification_id: Optional[int] = Field(
        default=None, foreign_key="classifications.id", primary_key=True
    )


class Classification(SQLModel, table=True):
    __tablename__ = "classifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    # Soft delete
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    games: List["Game"] = Relationship(
        back_populates="classifications", link_model=GameClassificationLink
    )


class Game(SQLModel, table=True):
    __tablename__ = "games"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(unique=True, index=True, max_length=200)
    description: str = Field(max_length=2000)
    developer: str = Field(max_length=150)
    publisher: str = Field(max_length=150)
    release_date: Optional[date] = Field(default=None)

    # Precio base en CLP
    price: float = Field(ge=0)

    # Ofertas automáticas según vigencia
    discount_percent: int = Field(default=0, ge=0, le=100)
    offer_start_date: Optional[datetime] = Field(default=None)
    offer_end_date: Optional[datetime] = Field(default=None)

    # Imágenes para Cloudinary
    image_url: Optional[str] = Field(default=None, max_length=500)
    image_public_id: Optional[str] = Field(default=None, max_length=255)

    # Soft delete
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    classifications: List[Classification] = Relationship(
        back_populates="games", link_model=GameClassificationLink
    )
