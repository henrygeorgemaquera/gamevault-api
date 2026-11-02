import os
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./gamevault.db")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    # Sin dominio propio Resend solo permite este remitente de pruebas
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")

    # Código de verificación: minutos de vida, intentos máximos y minutos de bloqueo
    VERIFICATION_CODE_EXPIRE_MINUTES: int = int(os.getenv("VERIFICATION_CODE_EXPIRE_MINUTES", "10"))
    VERIFICATION_MAX_ATTEMPTS: int = int(os.getenv("VERIFICATION_MAX_ATTEMPTS", "5"))
    VERIFICATION_LOCK_MINUTES: int = int(os.getenv("VERIFICATION_LOCK_MINUTES", "15"))

    # Jobs programados: plazo para verificar la cuenta y cada cuánto corren
    UNVERIFIED_ACCOUNT_TTL_HOURS: int = int(os.getenv("UNVERIFIED_ACCOUNT_TTL_HOURS", "24"))
    JOBS_INTERVAL_MINUTES: int = int(os.getenv("JOBS_INTERVAL_MINUTES", "60"))

    # Rate limiting por IP (formato slowapi: "<n>/<minute|hour|second>")
    RATE_LIMIT_REGISTER: str = os.getenv("RATE_LIMIT_REGISTER", "5/minute")
    RATE_LIMIT_VERIFY: str = os.getenv("RATE_LIMIT_VERIFY", "10/minute")
    RATE_LIMIT_LOGIN: str = os.getenv("RATE_LIMIT_LOGIN", "10/minute")
    RATE_LIMIT_LOGOUT: str = os.getenv("RATE_LIMIT_LOGOUT", "30/minute")

    # Se llama al iniciar la app para no arrancar sin clave JWT
    def validate(self) -> None:
        if not self.JWT_SECRET_KEY:
            raise RuntimeError("JWT_SECRET_KEY no está definido en el archivo .env")


settings = Settings()
