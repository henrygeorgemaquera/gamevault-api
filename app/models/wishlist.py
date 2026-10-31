from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class WishlistItem(SQLModel, table=True):
    __tablename__ = "wishlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "game_id", name="uq_wishlist_user_game"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    game_id: int = Field(foreign_key="games.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
