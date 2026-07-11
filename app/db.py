import os
from collections.abc import Iterable
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Connection, create_engine, delete, tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.pool import StaticPool

from app.models import Base, Inventory, Item, OrderableItem, OrderRecommendation

DEFAULT_DB_PATH = os.environ.get("APP_DB_PATH", "app.db")


def _make_engine(db_path: str):
    if db_path == ":memory:":
        # Shared connection for the engine's lifetime.
        return create_engine(
            "sqlite://",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    return create_engine(f"sqlite:///{db_path}")


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Create the schema (idempotent) at the given path, if it doesn't exist yet."""
    engine = _make_engine(db_path)
    Base.metadata.create_all(engine)
    engine.dispose()


@contextmanager
def get_connection(db_path: str = DEFAULT_DB_PATH) -> Iterator[Connection]:
    """Yield a connection in an open transaction, ensuring the schema exists."""
    engine = _make_engine(db_path)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        yield conn


def upsert_items(conn: Connection, rows: Iterable[dict]) -> None:
    rows = list(rows)
    if not rows:
        return
    stmt = sqlite_insert(Item).values(rows)
    update_cols = ("name", "category", "is_bio", "purchase_price", "suggested_retail_price")
    stmt = stmt.on_conflict_do_update(
        index_elements=["item_number"],
        set_={col: stmt.excluded[col] for col in update_cols},
    )
    conn.execute(stmt)


def upsert_inventory(conn: Connection, rows: Iterable[dict]) -> None:
    """Replace the (store_id, day) snapshots covered by rows, then insert them.

    Each upload represents the full inventory for a store on a given day, so
    rows dropped from a re-upload must be deleted rather than left stale.
    """
    rows = list(rows)
    if not rows:
        return
    scopes = {(row["store_id"], row["day"]) for row in rows}
    conn.execute(
        delete(Inventory).where(tuple_(Inventory.store_id, Inventory.day).in_(scopes))
    )
    stmt = sqlite_insert(Inventory).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["store_id", "item_number", "day"],
        set_={"quantity": stmt.excluded["quantity"]},
    )
    conn.execute(stmt)


def upsert_orderable_items(conn: Connection, rows: Iterable[dict]) -> None:
    """Replace the (store_id, ordering_day) snapshots covered by rows, then insert them.

    Each upload represents the full orderable-items set for a store on a given
    ordering day, so rows dropped from a re-upload must be deleted rather than
    left stale.
    """
    rows = list(rows)
    if not rows:
        return
    scopes = {(row["store_id"], row["ordering_day"]) for row in rows}
    conn.execute(
        delete(OrderableItem).where(
            tuple_(OrderableItem.store_id, OrderableItem.ordering_day).in_(scopes)
        )
    )
    stmt = sqlite_insert(OrderableItem).values(rows)
    update_cols = (
        "delivery_day",
        "purchase_price",
        "suggested_retail_price",
        "profit_margin",
        "tags",
        "category",
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["store_id", "item_number", "ordering_day"],
        set_={col: stmt.excluded[col] for col in update_cols},
    )
    conn.execute(stmt)


def upsert_order_recommendations(conn: Connection, rows: Iterable[dict]) -> None:
    """Replace the (store_id, ordering_day) snapshots covered by rows, then insert them.

    Each upload represents the full recommendation set for a store on a given
    ordering day, so rows dropped from a re-upload must be deleted rather than
    left stale.
    """
    rows = list(rows)
    if not rows:
        return
    scopes = {(row["store_id"], row["ordering_day"]) for row in rows}
    conn.execute(
        delete(OrderRecommendation).where(
            tuple_(OrderRecommendation.store_id, OrderRecommendation.ordering_day).in_(scopes)
        )
    )
    stmt = sqlite_insert(OrderRecommendation).values(rows)
    update_cols = ("delivery_day", "recommended_quantity")
    stmt = stmt.on_conflict_do_update(
        index_elements=["store_id", "item_number", "ordering_day"],
        set_={col: stmt.excluded[col] for col in update_cols},
    )
    conn.execute(stmt)
