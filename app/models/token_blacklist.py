from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


# Tokens JWT invalidados al cerrar sesión
class TokenBlacklist(SQLModel, table=True):
    __tablename__ = "token_blacklist"

    id: Optional[int] = Field(default=None, primary_key=True)
    # jti es el identificador único del token (no se guarda el token completo)
    jti: str = Field(unique=True, index=True, max_length=64)
    # Cuando el token expira solo, ya se puede borrar de esta tabla
    expires_at: datetime = Field(index=True)
