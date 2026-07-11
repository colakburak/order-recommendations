from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.ingestion.cleaners import (
    QUANTITY_OUTLIER_THRESHOLD,
    blank_to_none,
    clamp_non_negative,
    clean_whitespace,
    coerce_item_number,
    normalize_category,
    normalize_store_id,
    normalize_tags,
    parse_date,
)
from app.schemas import InventoryRow, ItemRow, OrderableItemRow, OrderRecommendationRow

FLAG_DESCRIPTIONS: dict[str, str] = {
    "quantity_outlier": f"Quantity exceeds {QUANTITY_OUTLIER_THRESHOLD} units; kept as-is, flagged for monitoring.",
    "clamped_negative_quantity": "Negative recommended_quantity; clamped to 0.",
}


ModelT = TypeVar("ModelT", bound=BaseModel)


def _validate(model_cls: type[ModelT], cleaned: dict) -> ModelT | None:
    try:
        return model_cls.model_validate(cleaned)
    except ValidationError:
        return None


def clean_item_row(raw: dict[str, str]) -> tuple[ItemRow | None, list[str]]:
    cleaned = {
        "item_number": raw.get("item_number"),
        "name": clean_whitespace(raw.get("name")),
        "category": normalize_category(raw.get("category")),
        "is_bio": raw.get("is_bio"),
        "purchase_price": raw.get("purchase_price"),
        "suggested_retail_price": raw.get("suggested_retail_price"),
    }
    return _validate(ItemRow, cleaned), []


def clean_inventory_row(raw: dict[str, str]) -> tuple[InventoryRow | None, list[str]]:
    cleaned = {
        "store_id": normalize_store_id(raw.get("store_id")),
        "item_number": raw.get("item_number"),
        "day": parse_date(raw.get("day")),
        "quantity": raw.get("quantity"),
    }
    row = _validate(InventoryRow, cleaned)
    if row is None:
        return None, []

    flags = []
    if row.quantity > QUANTITY_OUTLIER_THRESHOLD:
        flags.append("quantity_outlier")
    return row, flags


def clean_orderable_item_row(raw: dict[str, str]) -> tuple[OrderableItemRow | None, list[str]]:
    # Only known columns are read off `raw` by key, so rows with an extra
    # trailing-comma field (the unnamed 10th column) are naturally tolerated:
    # the extra key is simply never accessed, and the row is kept, not dropped.
    cleaned = {
        "store_id": normalize_store_id(raw.get("store_id")),
        "item_number": raw.get("item_number"),
        "ordering_day": raw.get("ordering_day"),
        "delivery_day": raw.get("delivery_day"),
        "purchase_price": blank_to_none(raw.get("purchase_price")),
        "suggested_retail_price": raw.get("suggested_retail_price"),
        "profit_margin": blank_to_none(raw.get("profit_margin")),
        "tags": normalize_tags(raw.get("tags")),
        "category": normalize_category(raw.get("category")),
    }
    return _validate(OrderableItemRow, cleaned), []


def clean_order_recommendation_row(raw: dict[str, str]) -> tuple[OrderRecommendationRow | None, list[str]]:
    flags = []
    raw_quantity = raw.get("recommended_quantity")
    if raw_quantity is None:
        return None, []
    try:
        quantity = float(raw_quantity)
    except ValueError:
        return None, []

    quantity, was_clamped = clamp_non_negative(quantity)
    if was_clamped:
        flags.append("clamped_negative_quantity")
    if quantity > QUANTITY_OUTLIER_THRESHOLD:
        flags.append("quantity_outlier")

    cleaned = {
        "store_id": normalize_store_id(raw.get("store_id")),
        "item_number": coerce_item_number(raw.get("item_number")),
        "ordering_day": raw.get("ordering_day"),
        "delivery_day": raw.get("delivery_day"),
        "recommended_quantity": quantity,
    }
    row = _validate(OrderRecommendationRow, cleaned)
    if row is None:
        return None, []
    return row, flags
