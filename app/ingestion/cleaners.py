import math
from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BeforeValidator, Field

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")


def clean_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Strip every value and read a blank cell as missing.

    Column-agnostic on purpose: it is the same for every CSV. Anything that depends on
    what a column *means* is declared on the schema field instead. Blank -> None lets
    required-vs-optional do the deciding: a blank optional field survives as None, a
    blank required one fails validation and the row is dropped.
    """
    return {key: (value.strip() or None) if isinstance(value, str) else value for key, value in raw.items()}


def _lower(value: Any) -> Any:
    return value.lower() if isinstance(value, str) else value


def _to_date(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return value


def _to_int(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return int(float(value))
    except ValueError:
        return value


def _to_pieces(value: Any) -> Any:
    try:
        return max(math.ceil(float(value)), 0)
    except (TypeError, ValueError):
        return value


# Every validator hands back what it cannot parse, so pydantic raises the error and the
# loader drops the row -- no cleaner needs to invent one.

# Keys are matched, not read: store_id, category, tags.
Key = Annotated[str, BeforeValidator(_lower)]

# Days arrive ISO or DD/MM/YYYY.
FlexDate = Annotated[date, BeforeValidator(_to_date)]

# Some item numbers are float-encoded, e.g. "1001.0".
ItemNumber = Annotated[int, BeforeValidator(_to_int)]

# An order is placed in whole pieces, so a fractional quantity rounds up rather than
# dropping the row, and a negative one clamps. Clamping has to happen here, before
# `ge=0` (and the table's CheckConstraint) would otherwise drop the row instead.
Pieces = Annotated[int, BeforeValidator(_to_pieces), Field(ge=0)]
