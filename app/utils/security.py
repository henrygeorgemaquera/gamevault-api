import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

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

# Lee el token del header Authorization (también habilita el botón Authorize de Swagger)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def utcnow() -> datetime:
    """UTC con zona horaria, como exige y devuelve el tipo datetime de SQLModel."""
    return datetime.now(timezone.utc)


# --- Contraseñas ---
# Genera el hash bcrypt (con salt incluido)
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# Compara la contraseña ingresada con el hash guardado
def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


# --- Códigos de verificación ---
# Código aleatorio de 6 dígitos (secrets es más seguro que random)
def generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


# El código también se guarda hasheado (HMAC con la clave secreta)
def hash_verification_code(code: str) -> str:
    return hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), code.encode("utf-8"), hashlib.sha256).hexdigest()


# compare_digest evita ataques por diferencia de tiempo
def verify_verification_code(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_verification_code(code), code_hash)


# --- JWT ---
# sub = id del usuario, jti = id único del token (para la blacklist)
def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# Valida firma y expiración; exige que existan exp, sub y jti
def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub", "jti"]},
    )


# --- Dependencias de autenticación ---
def _unauthorized(detail: str = "Token inválido o expirado") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


# Decodifica el token y revisa que no esté en la blacklist
def get_token_payload(
    token: str = Depends(oauth2_scheme),
    blacklist_repo: ITokenBlacklistRepository = Depends(get_token_blacklist_repository),
) -> dict:
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise _unauthorized()
    if blacklist_repo.exists(payload["jti"]):
        raise _unauthorized("Token revocado")
    return payload


# Devuelve el usuario dueño del token; se usa en las rutas protegidas
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
    return user
