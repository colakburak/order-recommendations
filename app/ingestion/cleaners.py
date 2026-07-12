import math
from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BeforeValidator, Field, ValidationInfo

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")


def _flag(info: ValidationInfo, name: str) -> None:
    """Record that this value needed fixing. No context means nobody is counting."""
    if info.context is not None:
        info.context.add(name)


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


def _to_pieces(value: Any, info: ValidationInfo) -> Any:
    try:
        pieces = math.ceil(float(value))
    except (TypeError, ValueError):
        return value
    if pieces < 0:
        _flag(info, "quantity_clamped")
        return 0
    return pieces


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
