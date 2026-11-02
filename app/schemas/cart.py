from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AddToCartRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"game_id": 1}})

    game_id: int = Field(gt=0, description="ID del título que se agrega al carrito")


class CartItemRead(BaseModel):
    game_id: int
    title: str
    image_url: Optional[str] = None
    price: float
    effective_discount_percent: int
    final_price: float
    # False si el título fue retirado del catálogo después de agregarlo
    is_available: bool
    # True si el usuario ya compró el título (no se puede comprar de nuevo)
    already_owned: bool


class CartRead(BaseModel):
    # Solo se entrega en carritos de invitado; hay que enviarlo en X-Cart-Token
    cart_token: Optional[str] = None
    items: List[CartItemRead] = []
    # Suma de los precios finales de los títulos disponibles y no comprados
    total: float
    # True si hay títulos no disponibles o ya comprados que bloquean la compra
    has_issues: bool
