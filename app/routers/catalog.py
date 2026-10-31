from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query

from app.schemas.catalog import (
    ClassificationRead,
    GameRead,
    PaginatedGamesResponse,
)
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/catalog", tags=["Catálogo Público"])


@router.get("/games", response_model=PaginatedGamesResponse)
def list_games(
    search: Optional[str] = Query(
        default=None,
        description="Búsqueda por título, descripción o desarrollador",
    ),
    classification_id: Optional[int] = Query(
        default=None, description="Filtrar por ID de clasificación/género"
    ),
    min_price: Optional[float] = Query(
        default=None, ge=0, description="Precio base mínimo"
    ),
    max_price: Optional[float] = Query(
        default=None, ge=0, description="Precio base máximo"
    ),
    on_sale: Optional[bool] = Query(
        default=None, description="Filtrar solo juegos con oferta vigente"
    ),
    sort_by: Literal["title", "price", "release_date", "created_at"] = Query(
        default="title", description="Campo de ordenamiento"
    ),
    sort_order: Literal["asc", "desc"] = Query(
        default="asc", description="Dirección de ordenamiento (asc o desc)"
    ),
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(
        default=10, ge=1, le=50, description="Cantidad de resultados por página"
    ),
    service: CatalogService = Depends(),
):
    return service.list_games(
        search=search,
        classification_id=classification_id,
        min_price=min_price,
        max_price=max_price,
        on_sale=on_sale,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/games/{game_id}", response_model=GameRead)
def get_game_detail(game_id: int, service: CatalogService = Depends()):
    return service.get_game_detail(game_id)


@router.get("/classifications", response_model=List[ClassificationRead])
def list_classifications(service: CatalogService = Depends()):
    return service.list_classifications()
