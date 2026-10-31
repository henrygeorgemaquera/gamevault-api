from datetime import date, timedelta

from sqlmodel import Session, select

from app.config.database import engine
from app.models.catalog import Classification, Game
from app.models.order import Order, OrderItem
from app.models.user import User
from app.models.wishlist import WishlistItem
from app.utils.security import hash_password, utcnow


def run_seed() -> None:
    now = utcnow()
    with Session(engine) as db:
        # Usuarios iniciales (Admin + Usuarios de prueba)
        if db.exec(select(User)).first() is None:
            admin = User(
                email="admin@gamevault.ucn.cl",
                hashed_password=hash_password("Admin123!"),
                is_verified=True,
                role="admin",
                is_active=True,
            )
            user1 = User(
                email="maria.torres@example.com",
                hashed_password=hash_password("Password123!"),
                is_verified=True,
                role="user",
                is_active=True,
            )
            user2 = User(
                email="carlos.rojas@example.com",
                hashed_password=hash_password("Password123!"),
                is_verified=True,
                role="user",
                is_active=True,
            )
            db.add_all([admin, user1, user2])
            db.commit()

        # Clasificaciones y Catálogo inicial
        if db.exec(select(Classification)).first() is None:
            c_accion = Classification(
                name="Acción",
                description="Juegos de combate rápido, reflejos y adrenalina.",
            )
            c_rpg = Classification(
                name="RPG",
                description="Juegos de rol con progresión de personajes e historia profunda.",
            )
            c_indie = Classification(
                name="Indie",
                description="Títulos desarrollados por estudios independientes.",
            )
            c_estrategia = Classification(
                name="Estrategia",
                description="Planificación táctica y gestión de recursos.",
            )
            c_aventura = Classification(
                name="Aventura",
                description="Exploración, narrativa y resolución de acertijos.",
            )
            db.add_all([c_accion, c_rpg, c_indie, c_estrategia, c_aventura])
            db.commit()

            for c in [c_accion, c_rpg, c_indie, c_estrategia, c_aventura]:
                db.refresh(c)

            games = [
                Game(
                    title="Elden Ring",
                    description="Un vasto mundo de fantasía oscura donde te aguardan peligros y descubrimientos.",
                    developer="FromSoftware",
                    publisher="Bandai Namco",
                    release_date=date(2022, 2, 25),
                    price=44990,
                    discount_percent=25,
                    offer_start_date=now - timedelta(days=2),
                    offer_end_date=now + timedelta(days=7),
                    image_url="https://placehold.co/600x800?text=Elden+Ring",
                    classifications=[c_accion, c_rpg, c_aventura],
                ),
                Game(
                    title="Hollow Knight",
                    description="Forja tu propio camino en Hallownest, un vasto reino en ruinas de insectos y héroes.",
                    developer="Team Cherry",
                    publisher="Team Cherry",
                    release_date=date(2017, 2, 24),
                    price=8990,
                    discount_percent=0,
                    image_url="https://placehold.co/600x800?text=Hollow+Knight",
                    classifications=[c_accion, c_indie, c_aventura],
                ),
                Game(
                    title="Baldur's Gate 3",
                    description="Reúne a tu grupo y regresa a los Reinos Olvidados en un relato de compañerismo y traición.",
                    developer="Larian Studios",
                    publisher="Larian Studios",
                    release_date=date(2023, 8, 3),
                    price=39990,
                    discount_percent=40,
                    offer_start_date=now - timedelta(days=1),
                    offer_end_date=now + timedelta(days=5),
                    image_url="https://placehold.co/600x800?text=Baldurs+Gate+3",
                    classifications=[c_rpg, c_estrategia, c_aventura],
                ),
                Game(
                    title="Cyberpunk 2077",
                    description="RPG de acción y aventura de mundo abierto ambientado en la megalópolis de Night City.",
                    developer="CD Projekt Red",
                    publisher="CD Projekt",
                    release_date=date(2020, 12, 10),
                    price=34990,
                    discount_percent=50,
                    offer_start_date=now - timedelta(days=20),
                    offer_end_date=now - timedelta(days=5),
                    image_url="https://placehold.co/600x800?text=Cyberpunk+2077",
                    classifications=[c_accion, c_rpg],
                ),
                Game(
                    title="Hades",
                    description="Desafía al dios de los muertos y protagoniza una salvaje fuga del Inframundo.",
                    developer="Supergiant Games",
                    publisher="Supergiant Games",
                    release_date=date(2020, 9, 17),
                    price=12500,
                    discount_percent=20,
                    offer_start_date=now - timedelta(days=3),
                    offer_end_date=now + timedelta(days=10),
                    image_url="https://placehold.co/600x800?text=Hades",
                    classifications=[c_accion, c_indie, c_rpg],
                ),
                Game(
                    title="The Day Before (Retirado)",
                    description="Título retirado del catálogo activo para probar soft delete.",
                    developer="Fntastic",
                    publisher="Mytona",
                    release_date=date(2023, 12, 7),
                    price=29990,
                    discount_percent=0,
                    is_active=False,
                    classifications=[c_accion],
                ),
            ]
            db.add_all(games)
            db.commit()

        # Datos semilla de Wishlist y Compras para el reporte de popularidad
        if db.exec(select(WishlistItem)).first() is None:
            users = list(db.exec(select(User).where(User.role == "user")).all())
            all_games = list(db.exec(select(Game)).all())
            if len(users) >= 2 and len(all_games) >= 3:
                u1, u2 = users[0], users[1]
                g1, g2, g3 = all_games[0], all_games[1], all_games[2]

                db.add_all(
                    [
                        WishlistItem(user_id=u1.id, game_id=g1.id, created_at=now - timedelta(days=3)),
                        WishlistItem(user_id=u2.id, game_id=g1.id, created_at=now - timedelta(days=1)),
                        WishlistItem(user_id=u1.id, game_id=g3.id, created_at=now - timedelta(days=2)),
                    ]
                )

                order1 = Order(
                    user_id=u1.id,
                    idempotency_key="seed-order-001",
                    total_amount=42732.5,
                    status="completed",
                    created_at=now - timedelta(days=2),
                )
                order2 = Order(
                    user_id=u2.id,
                    idempotency_key="seed-order-002",
                    total_amount=33742.5,
                    status="completed",
                    created_at=now - timedelta(days=1),
                )
                db.add_all([order1, order2])
                db.commit()
                db.refresh(order1)
                db.refresh(order2)

                db.add_all(
                    [
                        OrderItem(
                            order_id=order1.id,
                            game_id=g1.id,
                            game_title_snapshot=g1.title,
                            unit_price_snapshot=44990,
                            discount_percent_snapshot=25,
                            final_price_snapshot=33742.5,
                            created_at=order1.created_at,
                        ),
                        OrderItem(
                            order_id=order1.id,
                            game_id=g2.id,
                            game_title_snapshot=g2.title,
                            unit_price_snapshot=8990,
                            discount_percent_snapshot=0,
                            final_price_snapshot=8990,
                            created_at=order1.created_at,
                        ),
                        OrderItem(
                            order_id=order2.id,
                            game_id=g1.id,
                            game_title_snapshot=g1.title,
                            unit_price_snapshot=44990,
                            discount_percent_snapshot=25,
                            final_price_snapshot=33742.5,
                            created_at=order2.created_at,
                        ),
                    ]
                )
                db.commit()


if __name__ == "__main__":
    run_seed()
