from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.models.user import User
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
from app.schemas.auth import MessageResponse
from app.services.admin_service import AdminService
from app.utils.security import require_admin

router = APIRouter(
    prefix="/admin",
    tags=["Administración Backoffice"],
    dependencies=[Depends(require_admin)],
)


# --- Gestión de Clasificaciones ---
@router.get("/classifications", response_model=List[ClassificationAdminRead])
def list_all_classifications(
    include_inactive: bool = Query(
        default=True, description="Incluir clasificaciones eliminadas lógicamente"
    ),
    service: AdminService = Depends(),
):
    return service.list_classifications(include_inactive=include_inactive)


@router.post(
    "/classifications",
    response_model=ClassificationAdminRead,
    status_code=status.HTTP_201_CREATED,
)
def create_classification(
    data: ClassificationCreate, service: AdminService = Depends()
):
    return service.create_classification(data)


@router.put(
    "/classifications/{classification_id}",
    response_model=ClassificationAdminRead,
)
def update_classification(
    classification_id: int,
    data: ClassificationUpdate,
    service: AdminService = Depends(),
):
    return service.update_classification(classification_id, data)


@router.delete(
    "/classifications/{classification_id}", response_model=MessageResponse
)
def delete_classification(
    classification_id: int, service: AdminService = Depends()
):
    return MessageResponse(
        message=service.soft_delete_classification(classification_id)
    )


# --- Gestión de Títulos / Juegos ---
@router.get("/games", response_model=PaginatedAdminGamesResponse)
def list_all_games(
    include_inactive: bool = Query(
        default=True, description="Incluir juegos eliminados lógicamente"
    ),
    search: Optional[str] = Query(
        default=None, description="Buscar por título"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    service: AdminService = Depends(),
):
    return service.list_games(
        include_inactive=include_inactive,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/games",
    response_model=GameAdminRead,
    status_code=status.HTTP_201_CREATED,
)
def create_game(data: GameCreate, service: AdminService = Depends()):
    return service.create_game(data)


@router.put("/games/{game_id}", response_model=GameAdminRead)
def update_game(
    game_id: int, data: GameUpdate, service: AdminService = Depends()
):
    return service.update_game(game_id, data)


@router.delete("/games/{game_id}", response_model=MessageResponse)
def delete_game(game_id: int, service: AdminService = Depends()):
    return MessageResponse(message=service.soft_delete_game(game_id))


# --- 3. Gestión de Imágenes con Cloudinary ---
@router.post("/games/{game_id}/image", response_model=GameAdminRead)
def upload_game_image(
    game_id: int,
    file: UploadFile = File(..., description="Imagen en formato JPEG, PNG o WEBP"),
    width: int = Query(default=600, ge=100, le=2000, description="Ancho de transformación"),
    height: int = Query(default=800, ge=100, le=2000, description="Alto de transformación"),
    crop: Literal["fill", "fit", "scale", "thumb"] = Query(
        default="fill", description="Modo de recorte en Cloudinary"
    ),
    service: AdminService = Depends(),
):
    return service.upload_game_image(
        game_id=game_id, file=file, width=width, height=height, crop=crop
    )


@router.delete("/games/{game_id}/image", response_model=MessageResponse)
def delete_game_image_endpoint(
    game_id: int, service: AdminService = Depends()
):
    return MessageResponse(message=service.remove_game_image(game_id))


# --- Gestión de Usuarios y Suspensiones ---
@router.get("/users", response_model=PaginatedUsersResponse)
def list_users(
    search: Optional[str] = Query(
        default=None, description="Filtrar por correo electrónico"
    ),
    role: Optional[Literal["user", "admin"]] = Query(
        default=None, description="Filtrar por rol"
    ),
    is_active: Optional[bool] = Query(
        default=None, description="Filtrar por estado activo/suspendido"
    ),
    is_verified: Optional[bool] = Query(
        default=None, description="Filtrar por estado de verificación"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    service: AdminService = Depends(),
):
    return service.list_users(
        search=search,
        role=role,
        is_active=is_active,
        is_verified=is_verified,
        page=page,
        page_size=page_size,
    )


@router.patch("/users/{user_id}/suspend", response_model=UserAdminRead)
def suspend_user(
    user_id: int,
    current_admin: User = Depends(require_admin),
    service: AdminService = Depends(),
):
    return service.suspend_user(target_user_id=user_id, current_admin=current_admin)


@router.patch("/users/{user_id}/reactivate", response_model=UserAdminRead)
def reactivate_user(user_id: int, service: AdminService = Depends()):
    return service.reactivate_user(target_user_id=user_id)


# --- Reporte de Popularidad (Más Deseados y Más Comprados en un Período) ---
@router.get("/reports/popularity", response_model=PopularityReportResponse)
def get_popularity_report(
    start_date: Optional[datetime] = Query(
        default=None,
        description="Fecha/hora inicial del período (ISO 8601, ej: 2026-01-01T00:00:00Z)",
    ),
    end_date: Optional[datetime] = Query(
        default=None,
        description="Fecha/hora final del período (ISO 8601, ej: 2026-12-31T23:59:59Z)",
    ),
    limit: int = Query(
        default=10, ge=1, le=50, description="Cantidad máxima de títulos en el ranking"
    ),
    service: AdminService = Depends(),
):
    return service.get_popularity_report(
        start_date=start_date, end_date=end_date, limit=limit
    )
