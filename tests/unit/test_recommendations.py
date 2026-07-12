import pandas as pd

from app.recommendations import _or_none


def test_or_none_turns_nan_into_none():
    # NaN survives Optional[float] but is not JSON, so it must not reach the response.
    assert _or_none(float("nan")) is None
    assert _or_none(pd.NA) is None


def test_or_none_passes_real_values_through():
    assert _or_none(1.35) == 1.35
    assert _or_none(0.0) == 0.0
    assert _or_none("on_sale") == "on_sale"
