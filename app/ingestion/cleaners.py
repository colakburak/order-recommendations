from datetime import date, datetime
from typing import Optional

# Outlier quantities are kept, not corrected, just flagged for monitoring.
# Reused across inventory.csv and order_recommendations.csv (see ADR).
QUANTITY_OUTLIER_THRESHOLD = 1000

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")

_CATEGORIES = {
    "fruit": "fruits",
    "fruits": "fruits",
    "vegetable": "vegetables",
    "vegetables": "vegetables",
}


def clean_whitespace(value: Optional[str]) -> Optional[str]:
    """Remove leading/trailing whitespace"""
    return value.strip() if value else value

def normalize_category(value: Optional[str]) -> Optional[str]:
    """Normalize category names to a standard format [fruits, vegetables] or None"""
    if not value:
        return None
    return _CATEGORIES.get(value.strip().lower())

def normalize_store_id(value: Optional[str]) -> Optional[str]:
    """Normalize store_id casing/whitespace (e.g. ' Store_A ' -> 'store_a')"""
    return value.strip().lower() if value else value

def parse_date(value: Optional[str]) -> Optional[date]:
    """Parse ISO (YYYY-MM-DD) or DD/MM/YYYY dates, or return None if invalid"""
    if not value:
        return None
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None

def coerce_item_number(value: Optional[str]) -> Optional[int]:
    """Coerce item_number to an int, handling float-encoding (e.g. '1001.0'), or None if invalid"""
    if not value:
        return None
    try:
        return int(float(value.strip()))
    except ValueError:
        return None

def clamp_non_negative(value: float) -> tuple[float, bool]:
    """Clamp negative values to 0. Returns (clamped_value, was_clamped)"""
    return (0.0, True) if value < 0 else (value, False)

def normalize_tags(value: Optional[str]) -> Optional[str]:
    """Normalize a single tag's casing/whitespace -> new/price_change/on_sale, or None"""
    if not value:
        return None
    value = value.strip().lower()
    return value if value in ("new", "price_change", "on_sale") else None

def blank_to_none(value: Optional[str]) -> Optional[str]:
    """Turn an empty/whitespace-only string into None, otherwise pass through"""
    return value.strip() if value and value.strip() else None