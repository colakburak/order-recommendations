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
    rows_skipped: Counter[str] = Counter()
    rows: list[dict] = []
    for raw in reader:
        rows_processed += 1

        # A row with more fields than the header (a trailing comma) parks the surplus
        # under DictReader's `None` restkey. A row with fewer gets None for the columns
        # it omitted, which the schema already answers for -- required drops, optional keeps.
        # TODO: salvage the surplus-field rows instead of rejecting them.
        if None in raw:
            rows_skipped["malformed"] += 1
            continue

        try:
            row = dataset.row_schema.model_validate(clean_row(raw))
        except ValidationError:
            rows_skipped["invalid"] += 1
            continue

        rows.append(row.model_dump())

    with get_connection() as conn:
        upsert(conn, dataset, rows)

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
