from datetime import date

import pytest
from pydantic import ValidationError

from app.ingestion.cleaners import clean_row
from app.schemas import OrderRecommendationRow


def valid_row(**overrides) -> dict:
    row = {
        "store_id": "store_a",
        "item_number": "1001",
        "ordering_day": "2024-01-05",
        "delivery_day": "2024-01-06",
        "recommended_quantity": "10",
    }
    return row | overrides


def test_clean_row_strips_and_reads_blank_as_missing():
    assert clean_row({"name": "  Papaya  ", "tags": "   ", "is_bio": True}) == {
        "name": "Papaya",
        "tags": None,
        "is_bio": True,
    }


@pytest.mark.parametrize(
    "raw, field, expected",
    [
        # item numbers arrive float-encoded
        ({"item_number": "1001.0"}, "item_number", 1001),
        # days arrive ISO or DD/MM/YYYY
        ({"ordering_day": "2024-01-05"}, "ordering_day", date(2024, 1, 5)),
        ({"ordering_day": "05/01/2024"}, "ordering_day", date(2024, 1, 5)),
        # keys are matched, not read
        ({"store_id": "STORE_A"}, "store_id", "store_a"),
        # an order is placed in whole pieces, so a fraction rounds up
        ({"recommended_quantity": "2.3"}, "recommended_quantity", 3),
    ],
)
def test_cleaners_fix_what_they_can(raw, field, expected):
    row = OrderRecommendationRow.model_validate(valid_row(**raw), context=set())
    assert getattr(row, field) == expected


def test_negative_quantity_clamps_to_zero_and_is_flagged():
    flags: set[str] = set()

    row = OrderRecommendationRow.model_validate(
        valid_row(recommended_quantity="-5"), context=flags
    )

    assert row.recommended_quantity == 0
    assert flags == {"quantity_clamped"}


def test_unparseable_value_fails_validation_so_the_loader_drops_the_row():
    with pytest.raises(ValidationError):
        OrderRecommendationRow.model_validate(valid_row(item_number="abc"), context=set())
