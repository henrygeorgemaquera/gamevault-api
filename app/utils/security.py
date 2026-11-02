import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config.settings import settings
from app.models.user import User
from app.repositories.token_blacklist_repository import (
    ITokenBlacklistRepository,
    get_token_blacklist_repository,
)
from app.repositories.user_repository import IUserRepository, get_user_repository

logger = logging.getLogger(__name__)

# Lee el token del header Authorization (también habilita el botón Authorize de Swagger)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# Igual que el anterior, pero sin error si no viene token (rutas para invitados)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def utcnow() -> datetime:
    """UTC con zona horaria, como exige y devuelve el tipo datetime de SQLModel."""
    return datetime.now(timezone.utc)


# --- Contraseñas ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


# --- Códigos de verificación ---
def generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_code(code: str) -> str:
    return hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_verification_code(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_verification_code(code), code_hash)


# --- JWT ---
def create_access_token(user_id: int, role: str = "user") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub", "jti"]},
    )


# --- Dependencias de autenticación y autorización ---
def _unauthorized(detail: str = "Token inválido o expirado") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_token_payload(
    token: str = Depends(oauth2_scheme),
    blacklist_repo: ITokenBlacklistRepository = Depends(
        get_token_blacklist_repository
    ),
) -> dict:
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise _unauthorized()
    if blacklist_repo.exists(payload["jti"]):
        raise _unauthorized("Token revocado")
    return payload


def get_current_user(
    payload: dict = Depends(get_token_payload),
    user_repo: IUserRepository = Depends(get_user_repository),
) -> User:
    try:
        user_id = int(payload["sub"])
    except ValueError:
        raise _unauthorized()
    user = user_repo.get_by_id(user_id)
    if user is None or not user.is_verified:
        raise _unauthorized()
    if not user.is_active:
        logger.warning("Acceso denegado a cuenta suspendida: user_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta ha sido suspendida",
        )
    return user


# Sin token devuelve None (invitado); con un token inválido responde 401 como siempre
def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    blacklist_repo: ITokenBlacklistRepository = Depends(
        get_token_blacklist_repository
    ),
    user_repo: IUserRepository = Depends(get_user_repository),
) -> Optional[User]:
    if token is None:
        return None
    payload = get_token_payload(token, blacklist_repo)
    return get_current_user(payload, user_repo)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        logger.warning(
            "Acceso administrativo denegado para usuario sin permisos: user_id=%s, role=%s",
            current_user.id,
            current_user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: se requieren permisos de administrador",
        )
    return current_user
