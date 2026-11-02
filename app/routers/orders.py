from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Response, status

from app.models.user import User
from app.schemas.order import OrderRead, OrderSummaryRead
from app.services.order_service import OrderService, send_order_receipt
from app.utils.security import get_current_user

router = APIRouter(prefix="/orders", tags=["Pedidos"])


@router.post(
    "/checkout",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "Reintento: se devuelve el pedido ya creado"}},
)
def checkout(
    response: Response,
    background_tasks: BackgroundTasks,
    idempotency_key: str = Header(
        min_length=8,
        max_length=64,
        description=(
            "Clave única de esta compra (por ejemplo un UUID). Si se repite, "
            "no se crea otro pedido ni se reenvía la boleta"
        ),
    ),
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(),
):
    order, created = service.checkout(current_user, idempotency_key)
    if created:
        # La boleta se genera y se envía después de responder, sin bloquear al cliente
        background_tasks.add_task(send_order_receipt, order.id)
    else:
        # Reintento con la misma clave: 200 y sin reenviar la boleta
        response.status_code = status.HTTP_200_OK
    return order


@router.get("", response_model=List[OrderSummaryRead])
def list_orders(
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(),
):
    return service.list_orders(current_user)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(),
):
    return service.get_order(current_user, order_id)
