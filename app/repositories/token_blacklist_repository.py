from abc import ABC, abstractmethod
from datetime import datetime

from fastapi import Depends
from sqlmodel import Session, col, delete, select

from app.config.database import get_db
from app.models.token_blacklist import TokenBlacklist


# 1. EL CONTRATO: lo que el service puede pedirle al repositorio
class ITokenBlacklistRepository(ABC):
    @abstractmethod
    def add(self, jti: str, expires_at: datetime) -> None: ...

    @abstractmethod
    def exists(self, jti: str) -> bool: ...

    @abstractmethod
    def delete_expired(self, now: datetime) -> int: ...


# 2. LA IMPLEMENTACIÓN con SQLModel
class TokenBlacklistRepository(ITokenBlacklistRepository):
    def __init__(self, db: Session):
        self.db = db

    # Agrega el token a la lista negra (logout)
    def add(self, jti: str, expires_at: datetime) -> None:
        self.db.add(TokenBlacklist(jti=jti, expires_at=expires_at))
        self.db.commit()

    # Revisa si el token fue invalidado
    def exists(self, jti: str) -> bool:
        return self.db.exec(select(TokenBlacklist.id).where(TokenBlacklist.jti == jti)).first() is not None

    # Usado por el job: borra los tokens que ya expiraron solos
    def delete_expired(self, now: datetime) -> int:
        result = self.db.exec(delete(TokenBlacklist).where(col(TokenBlacklist.expires_at) < now))
        self.db.commit()
        return result.rowcount


# Aquí se elige la implementación concreta que recibe el service
def get_token_blacklist_repository(db: Session = Depends(get_db)) -> ITokenBlacklistRepository:
    return TokenBlacklistRepository(db)
