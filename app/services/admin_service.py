import logging
import math
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, HTTPException, UploadFile, status

from app.models.catalog import Classification, Game
from app.models.user import User
from app.repositories.admin_repository import (
    IAdminRepository,
    get_admin_repository,
)
from app.schemas.admin import (
    ClassificationAdminRead,
    ClassificationCreate,
    ClassificationUpdate,
    GameAdminRead,
    GameCreate,
    GameUpdate,
    PaginatedAdminGamesResponse,
    PaginatedUsersResponse,
    PopularityReportResponse,
    UserAdminRead,
)
from app.schemas.catalog import ClassificationRead
from app.services.catalog_service import calculate_game_pricing
from app.utils.cloudinary_client import (
    delete_game_image,
    upload_and_transform_game_image,
)
from app.utils.security import utcnow

logger = logging.getLogger(__name__)


def _to_game_admin_read(game: Game) -> GameAdminRead:
    is_on_sale, effective_discount, final_price = calculate_game_pricing(
        game, utcnow()
    )
    return GameAdminRead(
        id=game.id,
        title=game.title,
        description=game.description,
        developer=game.developer,
        publisher=game.publisher,
        release_date=game.release_date,
        price=game.price,
        discount_percent=game.discount_percent,
        offer_start_date=game.offer_start_date,
        offer_end_date=game.offer_end_date,
        is_on_sale=is_on_sale,
        effective_discount_percent=effective_discount,
        final_price=final_price,
        image_url=game.image_url,
        image_public_id=game.image_public_id,
        is_active=game.is_active,
        created_at=game.created_at,
        classifications=[
            ClassificationRead.model_validate(c) for c in game.classifications
        ],
    )


class AdminService:
    def __init__(
        self,
        admin_repo: IAdminRepository = Depends(get_admin_repository),
    ):
        self.admin_repo = admin_repo

    # --- Clasificaciones ---
    def list_classifications(
        self, include_inactive: bool = True
    ) -> List[ClassificationAdminRead]:
        items = self.admin_repo.list_classifications(
            include_inactive=include_inactive
        )
        return [ClassificationAdminRead.model_validate(c) for c in items]

    def create_classification(
        self, data: ClassificationCreate
    ) -> ClassificationAdminRead:
        name = data.name.strip()
        existing = self.admin_repo.get_classification_by_name(name)
        if existing is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Ya existe una clasificación con ese nombre",
            )
        classification = Classification(
            name=name, description=data.description, is_active=True
        )
        saved = self.admin_repo.save_classification(classification)
        logger.info("Clasificación creada por admin: id=%s, name=%s", saved.id, saved.name)
        return ClassificationAdminRead.model_validate(saved)

    def update_classification(
        self, classification_id: int, data: ClassificationUpdate
    ) -> ClassificationAdminRead:
        classification = self.admin_repo.get_classification_by_id(
            classification_id
        )
        if classification is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Clasificación no encontrada"
            )

        if data.name is not None:
            new_name = data.name.strip()
            existing = self.admin_repo.get_classification_by_name(new_name)
            if existing is not None and existing.id != classification.id:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Ya existe otra clasificación con ese nombre",
                )
            classification.name = new_name

        if data.description is not None:
            classification.description = data.description
        if data.is_active is not None:
            classification.is_active = data.is_active

        saved = self.admin_repo.save_classification(classification)
        return ClassificationAdminRead.model_validate(saved)

    def soft_delete_classification(self, classification_id: int) -> str:
        classification = self.admin_repo.get_classification_by_id(
            classification_id
        )
        if classification is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Clasificación no encontrada"
            )
        classification.is_active = False
        self.admin_repo.save_classification(classification)
        logger.info(
            "Clasificación eliminada lógicamente: id=%s", classification_id
        )
        return "Clasificación eliminada lógicamente"

    # --- Juegos / Títulos ---
    def list_games(
        self,
        include_inactive: bool = True,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedAdminGamesResponse:
        games, total = self.admin_repo.list_games(
            include_inactive=include_inactive,
            search=search,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        return PaginatedAdminGamesResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=[_to_game_admin_read(g) for g in games],
        )

    def _resolve_classifications(
        self, classification_ids: List[int]
    ) -> List[Classification]:
        unique_ids = list(dict.fromkeys(classification_ids))
        if not unique_ids:
            return []
        found = self.admin_repo.get_classifications_by_ids(unique_ids)
        if len(found) != len(unique_ids):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Una o más clasificaciones indicadas no existen",
            )
        inactive = [c.name for c in found if not c.is_active]
        if inactive:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"No se pueden asignar clasificaciones inactivas: {', '.join(inactive)}",
            )
        return found

    def create_game(self, data: GameCreate) -> GameAdminRead:
        title = data.title.strip()
        if self.admin_repo.get_game_by_title(title) is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Ya existe un título registrado con ese nombre",
            )

        classifications = self._resolve_classifications(data.classification_ids)

        game = Game(
            title=title,
            description=data.description.strip(),
            developer=data.developer.strip(),
            publisher=data.publisher.strip(),
            release_date=data.release_date,
            price=data.price,
            discount_percent=data.discount_percent,
            offer_start_date=data.offer_start_date,
            offer_end_date=data.offer_end_date,
            is_active=True,
            classifications=classifications,
        )
        saved = self.admin_repo.save_game(game)
        logger.info("Juego creado por admin: id=%s, title=%s", saved.id, saved.title)
        return _to_game_admin_read(saved)

    def update_game(self, game_id: int, data: GameUpdate) -> GameAdminRead:
        game = self.admin_repo.get_game_by_id(game_id)
        if game is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Título no encontrado"
            )

        if data.title is not None:
            new_title = data.title.strip()
            existing = self.admin_repo.get_game_by_title(new_title)
            if existing is not None and existing.id != game.id:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Ya existe otro título con ese nombre",
                )
            game.title = new_title

        if data.description is not None:
            game.description = data.description.strip()
        if data.developer is not None:
            game.developer = data.developer.strip()
        if data.publisher is not None:
            game.publisher = data.publisher.strip()
        if data.release_date is not None:
            game.release_date = data.release_date
        if data.price is not None:
            game.price = data.price
        if data.discount_percent is not None:
            game.discount_percent = data.discount_percent

        # Actualización de fechas de oferta si vienen en el payload
        fields_set = data.model_fields_set
        if "offer_start_date" in fields_set:
            game.offer_start_date = data.offer_start_date
        if "offer_end_date" in fields_set:
            game.offer_end_date = data.offer_end_date

        if (
            game.offer_start_date is not None
            and game.offer_end_date is not None
            and game.offer_start_date > game.offer_end_date
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "La fecha de inicio de la oferta no puede ser posterior a la fecha de término",
            )

        if data.is_active is not None:
            game.is_active = data.is_active

        if data.classification_ids is not None:
            game.classifications = self._resolve_classifications(
                data.classification_ids
            )

        saved = self.admin_repo.save_game(game)
        return _to_game_admin_read(saved)

    def soft_delete_game(self, game_id: int) -> str:
        game = self.admin_repo.get_game_by_id(game_id)
        if game is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Título no encontrado"
            )
        game.is_active = False
        self.admin_repo.save_game(game)
        logger.info("Juego eliminado lógicamente: id=%s", game_id)
        return "Título eliminado lógicamente del catálogo activo"

    # --- Imágenes con Cloudinary ---
    def upload_game_image(
        self,
        game_id: int,
        file: UploadFile,
        width: int = 600,
        height: int = 800,
        crop: str = "fill",
    ) -> GameAdminRead:
        game = self.admin_repo.get_game_by_id(game_id)
        if game is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Título no encontrado"
            )

        old_public_id = game.image_public_id
        image_url, public_id = upload_and_transform_game_image(
            file=file,
            game_id=game.id,
            width=width,
            height=height,
            crop=crop,
        )

        # Si tenía una imagen previa en Cloudinary, se elimina para no dejar huérfanos
        if old_public_id:
            delete_game_image(old_public_id)

        game.image_url = image_url
        game.image_public_id = public_id
        saved = self.admin_repo.save_game(game)
        return _to_game_admin_read(saved)

    def remove_game_image(self, game_id: int) -> str:
        game = self.admin_repo.get_game_by_id(game_id)
        if game is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Título no encontrado"
            )
        if not game.image_public_id and not game.image_url:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "El título no tiene una imagen asociada para eliminar",
            )

        if game.image_public_id:
            delete_game_image(game.image_public_id)

        game.image_url = None
        game.image_public_id = None
        self.admin_repo.save_game(game)
        return "Imagen eliminada correctamente"

    # --- Usuarios y Suspensiones ---
    def list_users(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedUsersResponse:
        users, total = self.admin_repo.list_users(
            search=search,
            role=role,
            is_active=is_active,
            is_verified=is_verified,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        return PaginatedUsersResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=[UserAdminRead.model_validate(u) for u in users],
        )

    def suspend_user(self, target_user_id: int, current_admin: User) -> UserAdminRead:
        if target_user_id == current_admin.id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "No puedes suspender tu propia cuenta de administrador",
            )
        user = self.admin_repo.get_user_by_id(target_user_id)
        if user is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Usuario no encontrado"
            )
        if user.role == "admin":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "No se puede suspender la cuenta de otro administrador",
            )
        user.is_active = False
        saved = self.admin_repo.save_user(user)
        logger.warning(
            "Cuenta suspendida por admin_id=%s: target_user_id=%s",
            current_admin.id,
            saved.id,
        )
        return UserAdminRead.model_validate(saved)

    def reactivate_user(self, target_user_id: int) -> UserAdminRead:
        user = self.admin_repo.get_user_by_id(target_user_id)
        if user is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Usuario no encontrado"
            )
        user.is_active = True
        saved = self.admin_repo.save_user(user)
        logger.info("Cuenta reactivada por admin: target_user_id=%s", saved.id)
        return UserAdminRead.model_validate(saved)

    # --- Reporte de Títulos más Deseados y Comprados ---
    def get_popularity_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
    ) -> PopularityReportResponse:
        if (
            start_date is not None
            and end_date is not None
            and start_date > end_date
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "La fecha de inicio del período no puede ser mayor que la fecha final",
            )

        most_purchased = self.admin_repo.get_most_purchased_games(
            start_date=start_date, end_date=end_date, limit=limit
        )
        most_wished = self.admin_repo.get_most_wished_games(
            start_date=start_date, end_date=end_date, limit=limit
        )

        return PopularityReportResponse(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            most_purchased=most_purchased,
            most_wished=most_wished,
        )
