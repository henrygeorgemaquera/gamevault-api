from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session

from app.config.database import engine
from app.config.settings import settings
from app.repositories.token_blacklist_repository import TokenBlacklistRepository
from app.repositories.user_repository import UserRepository
from app.utils.security import utcnow

# Corre en un hilo aparte mientras la app está levantada
scheduler = BackgroundScheduler()


# Los jobs no están dentro de una petición, por eso abren su propia sesión
def purge_unverified_users() -> None:
    cutoff = utcnow() - timedelta(hours=settings.UNVERIFIED_ACCOUNT_TTL_HOURS)
    with Session(engine) as db:
        UserRepository(db).delete_unverified_created_before(cutoff)


def purge_expired_tokens() -> None:
    with Session(engine) as db:
        TokenBlacklistRepository(db).delete_expired(utcnow())


# replace_existing evita duplicar los jobs si la app se recarga
def start_scheduler() -> None:
    scheduler.add_job(
        purge_unverified_users, "interval", minutes=settings.JOBS_INTERVAL_MINUTES,
        id="purge_unverified_users", replace_existing=True,
    )
    scheduler.add_job(
        purge_expired_tokens, "interval", minutes=settings.JOBS_INTERVAL_MINUTES,
        id="purge_expired_tokens", replace_existing=True,
    )
    scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
