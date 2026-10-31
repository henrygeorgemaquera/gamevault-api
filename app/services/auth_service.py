import logging
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.config.database import get_db
from app.config.settings import settings
from app.models.user import User
from app.repositories.token_blacklist_repository import (
    ITokenBlacklistRepository,
    get_token_blacklist_repository,
)
from app.repositories.user_repository import IUserRepository, get_user_repository
from app.schemas.auth import RegisterRequest, TokenResponse, VerifyCodeRequest
from app.utils.email import send_verification_email
from app.utils.security import (
    create_access_token,
    generate_verification_code,
    hash_password,
    hash_verification_code,
    utcnow,
    verify_password,
    verify_verification_code,
)

logger = logging.getLogger(__name__)

# Hash falso para que el login tarde igual cuando el correo no existe
_DUMMY_HASH = hash_password("dummy-password-for-timing")


class AuthService:
    # FastAPI inyecta la sesión y los repositorios (por sus interfaces)
    def __init__(
        self,
        db: Session = Depends(get_db),
        user_repo: IUserRepository = Depends(get_user_repository),
        blacklist_repo: ITokenBlacklistRepository = Depends(get_token_blacklist_repository),
    ):
        self.db = db
        self.user_repo = user_repo
        self.blacklist_repo = blacklist_repo

    # Crea el usuario sin verificar y le envía el código
    def register(self, data: RegisterRequest) -> str:
        email = data.email.lower()
        user = self.user_repo.get_by_email(email)

        if user is not None and user.is_verified:
            raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")

        if user is None:
            user = User(email=email, hashed_password=hash_password(data.password))
        # Si ya existía sin verificar se deja su contraseña original y solo se reenvía el código
        # (así nadie puede quedarse con un registro pendiente de otra persona)

        self._raise_if_locked(user)
        self._issue_code(user)
        return "Registro exitoso. Revisa tu correo para obtener el código de verificación"

    # Revisa el código: expiración, intentos y bloqueo
    def verify_code(self, data: VerifyCodeRequest) -> str:
        user = self.user_repo.get_by_email(data.email.lower())
        if user is None or user.is_verified:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código inválido")

        self._raise_if_locked(user)

        now = utcnow()
        if not user.verification_code_hash or not user.code_expires_at or user.code_expires_at < now:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "El código expiró, solicita uno nuevo")

        if not verify_verification_code(data.code, user.verification_code_hash):
            user.code_attempts += 1
            # Al llegar al máximo se bloquea y se invalida el código
            if user.code_attempts >= settings.VERIFICATION_MAX_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=settings.VERIFICATION_LOCK_MINUTES)
                user.code_attempts = 0
                user.verification_code_hash = None
                user.code_expires_at = None
            self.user_repo.save(user)
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código inválido")

        # Código correcto: se verifica la cuenta y se limpian los datos del código
        user.is_verified = True
        user.verification_code_hash = None
        user.code_expires_at = None
        user.code_attempts = 0
        user.locked_until = None
        self.user_repo.save(user)
        return "Cuenta verificada correctamente"

    # Recibe correo y contraseña ya extraídos del formulario OAuth2
    def login(self, email: str, password: str) -> TokenResponse:
        user = self.user_repo.get_by_email(email.lower())
        valid = verify_password(password, user.hashed_password if user else _DUMMY_HASH)
        # Mismo mensaje para correo o contraseña mala (no revela cuál falló)
        if user is None or not valid:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
        if not user.is_verified:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "La cuenta no ha sido verificada")
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Tu cuenta ha sido suspendida")
        return TokenResponse(access_token=create_access_token(user.id, user.role))

    # Guarda el jti del token en la blacklist hasta que expire
    def logout(self, payload: dict) -> str:
        expires_at = datetime.fromtimestamp(payload["exp"], timezone.utc)
        self.blacklist_repo.add(payload["jti"], expires_at)
        return "Sesión cerrada correctamente"

    # Si locked_until está en el futuro, el usuario sigue bloqueado
    def _raise_if_locked(self, user: User) -> None:
        if user.locked_until and user.locked_until > utcnow():
            raise HTTPException(
                status.HTTP_423_LOCKED,
                "Demasiados intentos fallidos, intenta nuevamente más tarde",
            )

    # Genera un código nuevo, lo guarda hasheado y lo envía por correo
    def _issue_code(self, user: User) -> None:
        code = generate_verification_code()
        user.verification_code_hash = hash_verification_code(code)
        user.code_expires_at = utcnow() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)
        user.code_attempts = 0
        user.locked_until = None
        self.user_repo.save(user)
        try:
            send_verification_email(user.email, code)
        except Exception:
            # El detalle del error queda en el log y al cliente solo se le da un mensaje general
            logger.exception("Falló el envío del correo de verificación")
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "No se pudo enviar el correo de verificación, intenta nuevamente",
            )
