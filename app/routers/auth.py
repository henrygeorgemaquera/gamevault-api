from fastapi import APIRouter, Depends, Request, status
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
from app.utils.rate_limit import limiter
from app.utils.security import get_current_user, get_token_payload

router = APIRouter(prefix="/auth", tags=["Autenticación"])


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
    service: AuthService = Depends(),
):
    # OAuth2 define el campo como "username"; aquí contiene el correo
    return service.login(form_data.username, form_data.password)


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
