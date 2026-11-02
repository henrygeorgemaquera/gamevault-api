from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.models.user import User
from app.schemas.cart import AddToCartRequest, CartRead
from app.services.cart_service import CartService
from app.utils.security import get_optional_user

# Todas las rutas sirven para invitados (X-Cart-Token) y para usuarios con sesión
router = APIRouter(prefix="/cart", tags=["Carrito"])

CART_TOKEN_DESCRIPTION = (
    "Token del carrito de invitado (se entrega al agregar el primer título). "
    "Se ignora si hay sesión iniciada"
)


@router.get("", response_model=CartRead)
def get_cart(
    x_cart_token: Optional[str] = Header(
        default=None, description=CART_TOKEN_DESCRIPTION
    ),
    current_user: Optional[User] = Depends(get_optional_user),
    service: CartService = Depends(),
):
    return service.get_cart(current_user, x_cart_token)


@router.post("/items", response_model=CartRead)
def add_item(
    data: AddToCartRequest,
    x_cart_token: Optional[str] = Header(
        default=None, description=CART_TOKEN_DESCRIPTION
    ),
    current_user: Optional[User] = Depends(get_optional_user),
    service: CartService = Depends(),
):
    return service.add_item(current_user, x_cart_token, data.game_id)


@router.delete("/items/{game_id}", response_model=CartRead)
def remove_item(
    game_id: int,
    x_cart_token: Optional[str] = Header(
        default=None, description=CART_TOKEN_DESCRIPTION
    ),
    current_user: Optional[User] = Depends(get_optional_user),
    service: CartService = Depends(),
):
    return service.remove_item(current_user, x_cart_token, game_id)
