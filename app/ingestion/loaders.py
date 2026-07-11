import csv
import io
import logging
from collections import Counter
from typing import Callable

from pydantic import BaseModel
from sqlalchemy import Connection

from app.db import (
    get_connection,
    upsert_inventory,
    upsert_items,
    upsert_orderable_items,
    upsert_order_recommendations,
)
from app.ingestion.pipelines import (
    FLAG_DESCRIPTIONS,
    clean_inventory_row,
    clean_item_row,
    clean_orderable_item_row,
    clean_order_recommendation_row,
)
from app.schemas import (
    FlagCount,
    InventoryRow,
    ItemRow,
    Metadata,
    OrderableItemRow,
    OrderRecommendationRow,
)

logger = logging.getLogger(__name__)


class InvalidCsvError(Exception):
    def __init__(self, filename: str, missing_columns: set[str]):
        self.filename = filename
        self.missing_columns = missing_columns
        super().__init__(f"{filename} is missing required columns: {sorted(missing_columns)}")


def _required_columns(row_model: type[BaseModel]) -> set[str]:
    return {name for name, info in row_model.model_fields.items() if info.is_required()}


def _load_rows(
    content: bytes,
    filename: str,
    clean_row_fn: Callable[[dict[str, str]], tuple[BaseModel | None, list[str]]],
    upsert_fn: Callable[[Connection, list[dict]], None],
    row_model: type[BaseModel],
) -> Metadata:
    reader = csv.DictReader(io.StringIO(content.decode()))

    missing_columns = _required_columns(row_model) - set(reader.fieldnames or [])
    if missing_columns:
        logger.warning("Rejected %s: missing required columns %s", filename, sorted(missing_columns))
        raise InvalidCsvError(filename, missing_columns)

    rows_processed = rows_skipped = 0
    flag_counter: Counter[str] = Counter()
    valid_rows = []
    for raw in reader:
        rows_processed += 1
        row, flags = clean_row_fn(raw)
        if row is None:
            rows_skipped += 1
            continue
        flag_counter.update(flags)
        valid_rows.append(row.model_dump())

    with get_connection() as conn:
        upsert_fn(conn, valid_rows)

    metadata = Metadata(
        file_name=filename,
        rows_processed=rows_processed,
        rows_inserted=len(valid_rows),
        rows_skipped=rows_skipped,
        flags=[
            FlagCount(reason=reason, description=FLAG_DESCRIPTIONS.get(reason, reason), count=count)
            for reason, count in sorted(flag_counter.items())
        ],
    )
    logger.info(
        "Loaded %s: %d/%d rows inserted, %d skipped",
        filename, metadata.rows_inserted, metadata.rows_processed, metadata.rows_skipped,
    )
    return metadata


def load_items(content: bytes, filename: str) -> Metadata:
    return _load_rows(
        content, filename, clean_item_row, upsert_items, ItemRow
    )


def load_inventory(content: bytes, filename: str) -> Metadata:
    return _load_rows(
        content, filename, clean_inventory_row, upsert_inventory, InventoryRow
    )


def load_orderable_items(content: bytes, filename: str) -> Metadata:
    return _load_rows(
        content, filename, clean_orderable_item_row, upsert_orderable_items, OrderableItemRow
    )


def load_order_recommendations(content: bytes, filename: str) -> Metadata:
    return _load_rows(
        content, filename, clean_order_recommendation_row, upsert_order_recommendations, OrderRecommendationRow
    )
