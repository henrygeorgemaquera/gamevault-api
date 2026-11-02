import logging
from typing import List, Optional, Tuple

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.config.database import engine
from app.models.order import Order, OrderItem
from app.models.user import User
from app.repositories.cart_repository import ICartRepository, get_cart_repository
from app.repositories.order_repository import IOrderRepository, get_order_repository
from app.repositories.user_repository import get_user_repository
from app.schemas.order import OrderItemRead, OrderRead, OrderSummaryRead
from app.services.catalog_service import calculate_game_pricing
from app.utils.email import send_order_confirmation_email
from app.utils.receipt import build_receipt_pdf
from app.utils.security import utcnow

logger = logging.getLogger(__name__)


def to_order_read(order: Order) -> OrderRead:
    items = sorted(order.items, key=lambda i: i.id)
    return OrderRead(
        id=order.id,
        status=order.status,
        total_amount=order.total_amount,
        created_at=order.created_at,
        items=[
            OrderItemRead(
                game_id=i.game_id,
                title=i.game_title_snapshot,
                unit_price=i.unit_price_snapshot,
                discount_percent=i.discount_percent_snapshot,
                final_price=i.final_price_snapshot,
            )
            for i in items
        ],
    )


# Tarea en segundo plano: genera la boleta y la envía por correo.
# Abre su propia sesión porque la de la petición ya se cerró al responder.
def send_order_receipt(order_id: int) -> None:
    with Session(engine) as db:
        # Se usan los providers (devuelven la interfaz) y no las clases concretas
        order_repo = get_order_repository(db)
        # Si otra tarea ya la envió (o la está enviando), no se repite
        if not order_repo.claim_receipt(order_id, utcnow()):
            logger.info("Boleta ya enviada, se omite: order_id=%s", order_id)
            return
        try:
            order = order_repo.get_by_id(order_id)
            buyer = get_user_repository(db).get_by_id(order.user_id)
            order_read = to_order_read(order)
            pdf_bytes = build_receipt_pdf(order_read, buyer.email)
            send_order_confirmation_email(buyer.email, order_read, pdf_bytes)
            logger.info("Boleta enviada: order_id=%s, user_id=%s", order_id, buyer.id)
        except Exception:
            # La compra ya está hecha; solo se libera la reserva y se deja el error en el log
            order_repo.release_receipt(order_id)
            logger.exception("No se pudo enviar la boleta: order_id=%s", order_id)


class OrderService:
    def __init__(
        self,
        order_repo: IOrderRepository = Depends(get_order_repository),
        cart_repo: ICartRepository = Depends(get_cart_repository),
    ):
        self.order_repo = order_repo
        self.cart_repo = cart_repo

    # Compra simulada. Retorna (pedido, creado): creado=False si fue un reintento
    def checkout(self, user: User, idempotency_key: str) -> Tuple[OrderRead, bool]:
        # La clave se liga al usuario para que dos usuarios no choquen entre sí
        key = f"{user.id}:{idempotency_key}"

        # Idempotencia: si la clave ya se usó, se devuelve el mismo pedido
        replay = self._find_existing_order(key, user)
        if replay is not None:
            return replay, False

        cart = self.cart_repo.get_by_user_id(user.id)
        cart_items = self.cart_repo.list_items(cart.id) if cart else []
        if not cart_items:
            # Un reintento simultáneo pudo comprar y vaciar el carrito justo antes
            replay = self._find_existing_order(key, user)
            if replay is not None:
                return replay, False
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "El carrito está vacío"
            )

        # Se revisa el estado actual de cada título contra la base de datos
        owned_ids = self.order_repo.get_owned_game_ids(user.id)
        problems = []
        for cart_item in cart_items:
            game = cart_item.game
            if not game.is_active:
                problems.append(f"'{game.title}' ya no está disponible")
            elif game.id in owned_ids:
                problems.append(f"'{game.title}' ya está en tu biblioteca")
        if problems:
            # Si esos "problemas" vienen de la compra de un reintento simultáneo,
            # se devuelve ese pedido en vez de un error
            replay = self._find_existing_order(key, user)
            if replay is not None:
                return replay, False
            logger.warning(
                "Compra rechazada: user_id=%s, motivo=%s", user.id, "; ".join(problems)
            )
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "No se puede completar la compra: " + "; ".join(problems),
            )

        # Detalle estático: se guarda el precio vigente en este momento
        order_items = []
        total = 0.0
        for cart_item in cart_items:
            game = cart_item.game
            _, discount, final_price = calculate_game_pricing(game)
            total += final_price
            order_items.append(
                OrderItem(
                    game_id=game.id,
                    game_title_snapshot=game.title,
                    unit_price_snapshot=game.price,
                    discount_percent_snapshot=discount,
                    final_price_snapshot=final_price,
                )
            )

        order = Order(
            user_id=user.id,
            idempotency_key=key,
            total_amount=round(total, 2),
            status="completed",
        )
        try:
            saved = self.order_repo.create_order(order, order_items, cart.id)
        except IntegrityError:
            # Otra petición con la misma clave se adelantó: se devuelve su pedido
            replay = self._find_existing_order(key, user)
            if replay is None:
                raise
            return replay, False

        logger.info(
            "Compra completada: order_id=%s, user_id=%s, total=%s, títulos=%s",
            saved.id,
            user.id,
            saved.total_amount,
            len(order_items),
        )
        return to_order_read(saved), True

    # Historial: resumen de cada pedido (el detalle completo está en get_order)
    def list_orders(self, user: User) -> List[OrderSummaryRead]:
        return [
            OrderSummaryRead(
                id=o.id,
                status=o.status,
                total_amount=o.total_amount,
                created_at=o.created_at,
                item_count=len(o.items),
            )
            for o in self.order_repo.list_by_user(user.id)
        ]

    def get_order(self, user: User, order_id: int) -> OrderRead:
        order = self.order_repo.get_by_id_for_user(order_id, user.id)
        if order is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
        return to_order_read(order)

    # Devuelve el pedido ya creado con esa clave (reintento), o None si no existe
    def _find_existing_order(self, key: str, user: User) -> Optional[OrderRead]:
        existing = self.order_repo.get_by_idempotency_key(key)
        if existing is None:
            return None
        logger.info("Reintento de compra: order_id=%s, user_id=%s", existing.id, user.id)
        return to_order_read(existing)
