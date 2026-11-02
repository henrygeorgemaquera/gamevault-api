from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Set

from fastapi import Depends
from sqlmodel import Session, col, delete, select, update

from app.config.database import get_db
from app.models.cart import CartItem
from app.models.order import Order, OrderItem


# 1. EL CONTRATO: lo que el service puede pedirle al repositorio
class IOrderRepository(ABC):
    @abstractmethod
    def get_owned_game_ids(self, user_id: int) -> Set[int]: ...

    @abstractmethod
    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Order]: ...

    @abstractmethod
    def create_order(
        self, order: Order, items: List[OrderItem], cart_id: int
    ) -> Order: ...

    @abstractmethod
    def list_by_user(self, user_id: int) -> List[Order]: ...

    @abstractmethod
    def get_by_id_for_user(self, order_id: int, user_id: int) -> Optional[Order]: ...

    @abstractmethod
    def get_by_id(self, order_id: int) -> Optional[Order]: ...

    @abstractmethod
    def claim_receipt(self, order_id: int, claimed_at: datetime) -> bool: ...

    @abstractmethod
    def release_receipt(self, order_id: int) -> None: ...


# 2. LA IMPLEMENTACIÓN con SQLModel
class OrderRepository(IOrderRepository):
    def __init__(self, db: Session):
        self.db = db

    # Títulos que el usuario ya compró (su biblioteca), según sus pedidos completados
    def get_owned_game_ids(self, user_id: int) -> Set[int]:
        statement = (
            select(col(OrderItem.game_id))
            .join(Order, col(Order.id) == col(OrderItem.order_id))
            .where(col(Order.user_id) == user_id, col(Order.status) == "completed")
            .distinct()
        )
        return set(self.db.exec(statement).all())

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Order]:
        statement = select(Order).where(col(Order.idempotency_key) == idempotency_key)
        return self.db.exec(statement).first()

    # Transacción atómica: pedido + detalle + vaciado del carrito con un solo commit.
    # Si algo falla, rollback y no queda nada a medias.
    def create_order(
        self, order: Order, items: List[OrderItem], cart_id: int
    ) -> Order:
        try:
            self.db.add(order)
            # flush asigna el id del pedido sin confirmar todavía la transacción
            self.db.flush()
            for item in items:
                item.order_id = order.id
                self.db.add(item)
            self.db.exec(delete(CartItem).where(col(CartItem.cart_id) == cart_id))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(order)
        return order

    # Historial del usuario: los más recientes primero
    def list_by_user(self, user_id: int) -> List[Order]:
        statement = (
            select(Order)
            .where(col(Order.user_id) == user_id)
            .order_by(col(Order.created_at).desc(), col(Order.id).desc())
        )
        return list(self.db.exec(statement).all())

    # Filtra también por usuario para que nadie vea pedidos ajenos
    def get_by_id_for_user(self, order_id: int, user_id: int) -> Optional[Order]:
        statement = select(Order).where(
            col(Order.id) == order_id, col(Order.user_id) == user_id
        )
        return self.db.exec(statement).first()

    def get_by_id(self, order_id: int) -> Optional[Order]:
        return self.db.get(Order, order_id)

    # Reserva el envío de la boleta: solo la primera llamada obtiene True,
    # así no se envía dos veces aunque haya tareas simultáneas
    def claim_receipt(self, order_id: int, claimed_at: datetime) -> bool:
        result = self.db.exec(
            update(Order)
            .where(col(Order.id) == order_id, col(Order.receipt_sent_at).is_(None))
            .values(receipt_sent_at=claimed_at)
        )
        self.db.commit()
        return result.rowcount == 1

    # Si el envío falla, se libera la reserva para poder reintentar después
    def release_receipt(self, order_id: int) -> None:
        self.db.exec(
            update(Order).where(col(Order.id) == order_id).values(receipt_sent_at=None)
        )
        self.db.commit()


# Aquí se elige la implementación concreta que recibe el service
def get_order_repository(db: Session = Depends(get_db)) -> IOrderRepository:
    return OrderRepository(db)
