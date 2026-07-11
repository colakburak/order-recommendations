import logging
from datetime import date

import pandas as pd
from sqlalchemy import select

from app.db import get_connection
from app.models import Inventory, Item, OrderableItem, OrderRecommendation
from app.schemas import Recommendation

logger = logging.getLogger(__name__)


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

    # INNER JOIN: orderable_items is the validity gate (excludes special
    # codes like 9901-9903, which are never marked orderable). It also
    # supplies `category`, which - unlike the items catalog - is guaranteed
    # present for every row here, sidestepping the "ghost item" gap below.
    merged = order_recs.merge(
        orderable[["store_id", "item_number", "ordering_day", "category"]],
        on=["store_id", "item_number", "ordering_day"],
        how="inner",
    )
    if merged.empty:
        return []

    # LEFT JOIN: items catalog, name only. Ghost items (e.g. 1099) have no
    # catalog entry; they're still served, with a fallback name.
    merged = merged.merge(items[["item_number", "name"]], on="item_number", how="left")
    ghost_mask = merged["name"].isna()
    if ghost_mask.any():
        logger.warning(
            "Catalog gap: item_number(s) %s orderable but missing from items catalog",
            sorted(merged.loc[ghost_mask, "item_number"].unique().tolist()),
        )
    merged["name"] = merged["name"].fillna(merged["item_number"].astype(str))

    # LEFT JOIN: current inventory as of the ordering day. Missing snapshots
    # default to 0 rather than dropping the recommendation.
    merged = merged.merge(
        inventory[["store_id", "item_number", "day", "quantity"]],
        left_on=["store_id", "item_number", "ordering_day"],
        right_on=["store_id", "item_number", "day"],
        how="left",
    )
    merged["quantity"] = merged["quantity"].fillna(0.0)

    return [
        Recommendation(
            item_number=row.item_number,
            name=row.name,
            category=row.category,
            current_inventory=row.quantity,
            recommended_quantity=row.recommended_quantity,
            delivery_day=row.delivery_day,
        )
        for row in merged.itertuples()
    ]
