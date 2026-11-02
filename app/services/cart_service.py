import logging
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, status

from app.models.cart import Cart
from app.models.user import User
from app.repositories.cart_repository import ICartRepository, get_cart_repository
from app.repositories.catalog_repository import (
    ICatalogRepository,
    get_catalog_repository,
)
from app.repositories.order_repository import IOrderRepository, get_order_repository
from app.schemas.cart import CartItemRead, CartRead
from app.services.catalog_service import calculate_game_pricing

logger = logging.getLogger(__name__)


class CartService:
    def __init__(
        self,
        cart_repo: ICartRepository = Depends(get_cart_repository),
        catalog_repo: ICatalogRepository = Depends(get_catalog_repository),
        order_repo: IOrderRepository = Depends(get_order_repository),
    ):
        self.cart_repo = cart_repo
        self.catalog_repo = catalog_repo
        self.order_repo = order_repo

    # --- Operaciones del carrito (usuario registrado o invitado) ---
    def get_cart(self, user: Optional[User], cart_token: Optional[str]) -> CartRead:
        cart = self._find_cart(user, cart_token)
        return self._build_cart_read(cart, user)

    def add_item(
        self, user: Optional[User], cart_token: Optional[str], game_id: int
    ) -> CartRead:
        game = self.catalog_repo.get_active_game_by_id(game_id)
        if game is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Título no encontrado o no disponible"
            )

        # Juegos digitales: no se puede comprar dos veces el mismo título
        if user is not None and game_id in self.order_repo.get_owned_game_ids(user.id):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Ya tienes este título en tu biblioteca"
            )

        cart = self._get_or_create_cart(user, cart_token)
        if self.cart_repo.has_item(cart.id, game_id):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "El título ya está en el carrito"
            )

        self.cart_repo.add_items(cart.id, [game_id])
        return self._build_cart_read(cart, user)

    def remove_item(
        self, user: Optional[User], cart_token: Optional[str], game_id: int
    ) -> CartRead:
        cart = self._find_cart(user, cart_token)
        if cart is None or not self.cart_repo.remove_item(cart.id, game_id):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "El título no está en el carrito"
            )
        return self._build_cart_read(cart, user)

    # --- Fusión del carrito de invitado al iniciar sesión ---
    def merge_guest_cart(self, user_id: int, guest_token: str) -> None:
        guest_cart = self.cart_repo.get_by_guest_token(guest_token)
        if guest_cart is None:
            return

        user_cart = self.cart_repo.get_by_user_id(user_id)
        if user_cart is None:
            user_cart = self.cart_repo.create(user_id=user_id)

        owned_ids = self.order_repo.get_owned_game_ids(user_id)
        already_in_cart = {i.game_id for i in self.cart_repo.list_items(user_cart.id)}

        # Se traen solo títulos disponibles, no comprados y que no estén repetidos
        to_add = [
            item.game_id
            for item in self.cart_repo.list_items(guest_cart.id)
            if item.game is not None
            and item.game.is_active
            and item.game_id not in owned_ids
            and item.game_id not in already_in_cart
        ]
        self.cart_repo.add_items(user_cart.id, to_add)
        self.cart_repo.delete_cart(guest_cart)
        logger.info(
            "Carrito de invitado fusionado: user_id=%s, títulos_agregados=%s",
            user_id,
            len(to_add),
        )

    # --- Apoyo interno ---
    def _find_cart(
        self, user: Optional[User], cart_token: Optional[str]
    ) -> Optional[Cart]:
        if user is not None:
            return self.cart_repo.get_by_user_id(user.id)
        if cart_token:
            return self.cart_repo.get_by_guest_token(cart_token)
        return None

    def _get_or_create_cart(
        self, user: Optional[User], cart_token: Optional[str]
    ) -> Cart:
        cart = self._find_cart(user, cart_token)
        if cart is not None:
            return cart
        if user is not None:
            return self.cart_repo.create(user_id=user.id)
        # Invitado sin carrito (o con token desconocido): se le crea uno nuevo
        return self.cart_repo.create(guest_token=secrets.token_urlsafe(32))

    # Arma la respuesta con el precio y la disponibilidad actuales de cada título
    def _build_cart_read(self, cart: Optional[Cart], user: Optional[User]) -> CartRead:
        if cart is None:
            return CartRead(items=[], total=0.0, has_issues=False)

        owned_ids = self.order_repo.get_owned_game_ids(user.id) if user else set()
        items = []
        total = 0.0
        has_issues = False

        for cart_item in self.cart_repo.list_items(cart.id):
            game = cart_item.game
            _, effective_discount, final_price = calculate_game_pricing(game)
            is_available = game.is_active
            already_owned = game.id in owned_ids

            if is_available and not already_owned:
                total += final_price
            else:
                has_issues = True

            items.append(
                CartItemRead(
                    game_id=game.id,
                    title=game.title,
                    image_url=game.image_url,
                    price=game.price,
                    effective_discount_percent=effective_discount,
                    final_price=final_price,
                    is_available=is_available,
                    already_owned=already_owned,
                )
            )

        return CartRead(
            cart_token=cart.guest_token,
            items=items,
            total=round(total, 2),
            has_issues=has_issues,
        )
