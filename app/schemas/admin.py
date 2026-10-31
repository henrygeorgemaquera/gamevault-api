from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.schemas.catalog import ClassificationRead


# --- Clasificaciones (Backoffice) ---
class ClassificationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class ClassificationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


class ClassificationAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime


# --- Juegos / Títulos (Backoffice) ---
class GameCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    developer: str = Field(min_length=2, max_length=150)
    publisher: str = Field(min_length=2, max_length=150)
    release_date: Optional[date] = None
    price: float = Field(ge=0)
    discount_percent: int = Field(default=0, ge=0, le=100)
    offer_start_date: Optional[datetime] = None
    offer_end_date: Optional[datetime] = None
    classification_ids: List[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_offer_dates(self) -> "GameCreate":
        if (
            self.offer_start_date is not None
            and self.offer_end_date is not None
            and self.offer_start_date > self.offer_end_date
        ):
            raise ValueError(
                "La fecha de inicio de la oferta no puede ser posterior a la fecha de término"
            )
        return self


class GameUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=2000)
    developer: Optional[str] = Field(default=None, min_length=2, max_length=150)
    publisher: Optional[str] = Field(default=None, min_length=2, max_length=150)
    release_date: Optional[date] = None
    price: Optional[float] = Field(default=None, ge=0)
    discount_percent: Optional[int] = Field(default=None, ge=0, le=100)
    offer_start_date: Optional[datetime] = None
    offer_end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    classification_ids: Optional[List[int]] = None


class GameAdminRead(BaseModel):
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
    is_on_sale: bool
    effective_discount_percent: int
    final_price: float
    image_url: Optional[str] = None
    image_public_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    classifications: List[ClassificationRead] = []


class PaginatedAdminGamesResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[GameAdminRead]


# --- Gestión de Usuarios (Backoffice) ---
class UserAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    is_verified: bool
    is_active: bool
    created_at: datetime


class PaginatedUsersResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[UserAdminRead]


# --- Reportes de Popularidad por Período ---
class MostPurchasedGameItem(BaseModel):
    game_id: int
    title: str
    is_active: bool
    purchase_count: int
    total_revenue: float


class MostWishedGameItem(BaseModel):
    game_id: int
    title: str
    is_active: bool
    wishlist_count: int


class PopularityReportResponse(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int
    most_purchased: List[MostPurchasedGameItem]
    most_wished: List[MostWishedGameItem]
