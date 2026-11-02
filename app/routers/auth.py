import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config.settings import settings
from app.models.user import User
from app.schemas.auth import (
    MessageResponse,
    RegisterRequest,
    TokenResponse,
    UserRead,
    VerifyCodeRequest,
)
from app.services.auth_service import AuthService
from app.services.cart_service import CartService
from app.utils.rate_limit import limiter
from app.utils.security import (
    decode_access_token,
    get_current_user,
    get_token_payload,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])
logger = logging.getLogger(__name__)


# slowapi necesita el parámetro "request" para saber la IP de quien llama
@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def register(request: Request, data: RegisterRequest, service: AuthService = Depends()):
    return MessageResponse(message=service.register(data))


@router.post("/verify", response_model=MessageResponse)
@limiter.limit(settings.RATE_LIMIT_VERIFY)
def verify(request: Request, data: VerifyCodeRequest, service: AuthService = Depends()):
    return MessageResponse(message=service.verify_code(data))


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    x_cart_token: Optional[str] = Header(
        default=None,
        description="Token del carrito de invitado que se fusiona con el del usuario",
    ),
    service: AuthService = Depends(),
    cart_service: CartService = Depends(),
):
    # OAuth2 define el campo como "username"; aquí contiene el correo
    token = service.login(form_data.username, form_data.password)

    # Si venía un carrito de invitado, se fusiona; un fallo aquí no debe impedir el login
    if x_cart_token:
        try:
            user_id = int(decode_access_token(token.access_token)["sub"])
            cart_service.merge_guest_cart(user_id, x_cart_token)
        except Exception:
            logger.exception("No se pudo fusionar el carrito de invitado")
    return token


# Requiere token válido; el service lo agrega a la blacklist
@router.post("/logout", response_model=MessageResponse)
@limiter.limit(settings.RATE_LIMIT_LOGOUT)
def logout(
    request: Request,
    payload: dict = Depends(get_token_payload),
    service: AuthService = Depends(),
):
    return MessageResponse(message=service.logout(payload))


# Ruta protegida de ejemplo: devuelve el usuario autenticado
@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user
