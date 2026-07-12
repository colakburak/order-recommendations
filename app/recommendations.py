import logging
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import select

from app.db import get_connection
from app.models import Inventory, Item, OrderableItem, OrderRecommendation
from app.schemas import Recommendation

logger = logging.getLogger(__name__)


def _or_none(value: Any) -> Any:
    """NaN -> None. Pydantic lets NaN through an Optional[float], and NaN is not JSON."""
    return None if pd.isna(value) else value


def fetch_recommendations(store_id: str, day: date) -> list[Recommendation]:
    with get_connection() as conn:
        order_recs = pd.read_sql_query(
            select(OrderRecommendation).where(
                OrderRecommendation.store_id == store_id,
                OrderRecommendation.ordering_day == day,
            ),
            conn,
        )
        if order_recs.empty:
            return []

        orderable = pd.read_sql_query(
            select(OrderableItem).where(
                OrderableItem.store_id == store_id,
                OrderableItem.ordering_day == day,
            ),
            conn,
        )
        inventory = pd.read_sql_query(
            select(Inventory).where(
                Inventory.store_id == store_id,
                Inventory.day == day,
            ),
            conn,
        )
        items = pd.read_sql_query(select(Item), conn)

    # INNER JOIN: orderable_items is the validity gate (excludes special codes 9901-9903,
    # never marked orderable) and holds this store's price for this day, which is what the
    # order is placed at. Projections stay narrow: an overlapping column (delivery_day
    # here, the catalog's prices below) would silently suffix into _x/_y.
    merged = order_recs.merge(
        orderable[
            [
                "store_id", "item_number", "ordering_day", "category",
                "purchase_price", "suggested_retail_price", "profit_margin", "tags",
            ]
        ],
        on=["store_id", "item_number", "ordering_day"],
        how="inner",
    )
    if merged.empty:
        return []

    # LEFT JOIN: name and is_bio only. Ghost items (e.g. 1099) have no catalog entry;
    # they're still served, with their item_number as a fallback name.
    merged = merged.merge(items[["item_number", "name", "is_bio"]], on="item_number", how="left")
    ghost_mask = merged["name"].isna()
    if ghost_mask.any():
        logger.warning(
            "Catalog gap: item_number(s) %s orderable but missing from items catalog",
            sorted(merged.loc[ghost_mask, "item_number"].unique().tolist()),
        )
    merged["name"] = merged["name"].fillna(merged["item_number"].astype(str))

    # LEFT JOIN: inventory on the ordering day. A missing snapshot means 0, not a dropped row.
    merged = merged.merge(
        inventory[["store_id", "item_number", "day", "quantity"]],
        left_on=["store_id", "item_number", "ordering_day"],
        right_on=["store_id", "item_number", "day"],
        how="left",
    )
    merged["quantity"] = merged["quantity"].fillna(0.0)

    recommendations = []
    for row in merged.itertuples():
        purchase_price = _or_none(row.purchase_price)
        recommendations.append(
            Recommendation(
                item_number=row.item_number,
                name=row.name,
                category=row.category,
                is_bio=_or_none(row.is_bio),
                tags=_or_none(row.tags),
                current_inventory=row.quantity,
                recommended_quantity=row.recommended_quantity,
                delivery_day=row.delivery_day,
                purchase_price=purchase_price,
                suggested_retail_price=row.suggested_retail_price,
                profit_margin=_or_none(row.profit_margin),
                # money, so round: 18 * 0.93 is 16.740000000000002 in float
                order_cost=(
                    round(row.recommended_quantity * purchase_price, 2)
                    if purchase_price is not None
                    else None
                ),
            )
        )
    return recommendations
