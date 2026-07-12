import csv
import io
import logging
from collections import Counter

from fastapi import HTTPException
from pydantic import ValidationError

from app.datasets import Dataset
from app.db import get_connection, upsert
from app.ingestion.cleaners import clean_row
from app.schemas import Metadata

logger = logging.getLogger(__name__)

def load(content: bytes, filename: str, dataset: Dataset) -> Metadata:
    """Read one uploaded CSV into the database"""

    reader = csv.DictReader(io.StringIO(content.decode()))

    missing_columns = dataset.required_columns - set(reader.fieldnames or [])
    if missing_columns:
        logger.warning("Rejected %s: missing required columns %s", filename, sorted(missing_columns))
        raise HTTPException(
            status_code=422,
            detail=f"{filename} is missing required columns: {', '.join(sorted(missing_columns))}",
        )

    rows_processed = 0
    rows_repaired = 0
    rows_skipped: Counter[str] = Counter()
    rows: list[dict] = []
    for raw in reader:
        rows_processed += 1

        # A trailing comma gives the row a surplus field, which DictReader parks under its
        # `None` restkey. Blank surplus -> the named fields are still aligned, so drop the
        # surplus and keep the row. Surplus with content -> a value held an unquoted comma
        # and every field after it shifted; which one is unknowable, so the row goes.
        # (A row with *fewer* fields needs nothing: DictReader gives the omitted columns
        # None, and the schema already answers for that -- required drops, optional keeps.)
        surplus = raw.pop(None, [])
        if any(value.strip() for value in surplus):
            rows_skipped["misaligned"] += 1
            continue
        if surplus:
            rows_repaired += 1

        try:
            row = dataset.row_schema.model_validate(clean_row(raw))
        except ValidationError:
            rows_skipped["invalid"] += 1
            continue

        rows.append(row.model_dump())

    with get_connection() as conn:
        upsert(conn, dataset, rows)

    if rows_repaired:
        logger.info("Repaired %d trailing-comma rows in %s", rows_repaired, filename)
    if rows_skipped:
        logger.warning(
            "Skipped %d rows in %s: %s", sum(rows_skipped.values()), filename, dict(rows_skipped)
        )
    logger.info("Loaded %s: %d/%d rows inserted", filename, len(rows), rows_processed)

    return Metadata(
        file_name=filename,
        rows_processed=rows_processed,
        rows_inserted=len(rows),
    )
