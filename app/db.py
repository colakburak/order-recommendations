import os
from collections.abc import Iterable
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Connection, create_engine, delete, tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.pool import StaticPool

from app.datasets import Dataset
from app.models import Base

DEFAULT_DB_PATH = os.environ.get("APP_DB_PATH", "app.db")

# SQLite caps bound parameters per statement at 32766
_INSERT_BATCH_SIZE = 500


def _chunked(rows: list[dict], size: int = _INSERT_BATCH_SIZE) -> Iterator[list[dict]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def _make_engine(db_path: str):
    if db_path == ":memory:":
        # One shared connection for the engine's lifetime -- otherwise every connection
        # would get its own empty database.
        return create_engine(
            "sqlite://",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    return create_engine(f"sqlite:///{db_path}")


# One engine (and one create_all) for the process, not one per request: a new engine per call
# means per-request DDL and a fresh connection pool each time -- and for ":memory:", a fresh
# empty database each time, since the data lives in the engine's connection.
ENGINE = _make_engine(DEFAULT_DB_PATH)
Base.metadata.create_all(ENGINE)


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Yield a connection in an open transaction."""
    with ENGINE.begin() as conn:
        yield conn


def upsert(conn: Connection, dataset: Dataset, rows: Iterable[dict]) -> None:
    """Replace the snapshots covered by `rows`, then insert them.

    An upload is the full picture for its scope (e.g. one store's inventory on one day),
    so rows dropped from a re-upload must be deleted rather than left stale. A dataset
    with no scope is a catalog shared across stores and days: nothing is deleted.
    """
    rows = list(rows)
    if not rows:
        return

    table = dataset.table_model
    if dataset.scope:
        scope_columns = [getattr(table, name) for name in dataset.scope]
        scopes = {tuple(row[name] for name in dataset.scope) for row in rows}
        conn.execute(delete(table).where(tuple_(*scope_columns).in_(scopes)))

    for batch in _chunked(rows):
        stmt = sqlite_insert(table).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=dataset.primary_key,
            set_={col: stmt.excluded[col] for col in dataset.update_columns},
        )
        conn.execute(stmt)