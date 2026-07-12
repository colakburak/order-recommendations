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
    details: Counter[str] = Counter()
    rows_skipped: Counter[str] = Counter()
    rows: list[dict] = []
    for raw in reader:
        rows_processed += 1
        # Cleaners record their fixes here
        row_flags: set[str] = set()

        # DictReader parks surplus fields under its `None` restkey. Blank surplus (trailing
        # comma) -> the named fields still line up, so keep the row. Surplus with content ->
        # an unquoted comma shifted everything after it, unknowably, so the row goes.
        surplus = raw.pop(None, [])
        if any(value.strip() for value in surplus):
            rows_skipped["misaligned"] += 1
            continue
        if surplus:
            row_flags.add("trailing_comma_fixed")

        try:
            row = dataset.row_schema.model_validate(clean_row(raw), context=row_flags)
        except ValidationError:
            rows_skipped["invalid"] += 1
            continue

        details.update(row_flags)
        rows.append(row.model_dump())

    with get_connection() as conn:
        upsert(conn, dataset, rows)

    if rows_skipped:
        logger.warning(
            "Skipped %d rows in %s: %s", sum(rows_skipped.values()), filename, dict(rows_skipped)
        )
    logger.info(
        "Loaded %s: %d/%d rows inserted, fixes %s", filename, len(rows), rows_processed, dict(details)
    )

    return Metadata(
        file_name=filename,
        rows_processed=rows_processed,
        rows_inserted=len(rows),
        details=dict(details),
    )
