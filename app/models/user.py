from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    # unique evita correos repetidos; index acelera la búsqueda al hacer login
    email: str = Field(unique=True, index=True, max_length=255)
    # Nunca se guarda la contraseña real, solo su hash bcrypt
    hashed_password: str
    is_verified: bool = Field(default=False)
    # Rol del usuario: "user" o "admin"
    role: str = Field(default="user", max_length=20)
    # False cuando un administrador suspende la cuenta (se usa desde el Módulo 3)
    is_active: bool = Field(default=True)
    # Fecha con zona horaria (UTC), que es lo que SQLModel espera
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Datos de la verificación por código (se limpian al verificar)
    verification_code_hash: Optional[str] = Field(default=None)
    code_expires_at: Optional[datetime] = Field(default=None)
    code_attempts: int = Field(default=0)
    # Si es una fecha futura, el usuario está bloqueado por demasiados intentos
    locked_until: Optional[datetime] = Field(default=None)
