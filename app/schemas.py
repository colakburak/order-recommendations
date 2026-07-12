from typing import Optional
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.ingestion.cleaners import FlexDate, ItemNumber, Key, Pieces

# CSV Row Schemas --------------
# One row of an upload, and how each raw cell becomes a typed value. `clean_row` has
# already stripped the cell and turned a blank one into None; the field types below carry
# whatever cleaning depends on what the column *means*.
class ItemRow(BaseModel):
    item_number: ItemNumber
    name: str
    category: Key
    is_bio: bool
    purchase_price: float
    suggested_retail_price: float

class InventoryRow(BaseModel):
    store_id: Key
    item_number: ItemNumber
    day: FlexDate
    # Stock is measured, not ordered, so it stays fractional as reported.
    quantity: float = Field(allow_inf_nan=False)

class OrderableItemRow(BaseModel):
    store_id: Key
    item_number: ItemNumber
    ordering_day: FlexDate
    delivery_day: FlexDate
    # purchase_price and profit_margin go missing together and neither decides
    # orderability, so a row without them is still worth keeping.
    purchase_price: Optional[float] = None
    suggested_retail_price: float
    profit_margin: Optional[float] = None
    tags: Optional[Key] = None
    category: Key

class OrderRecommendationRow(BaseModel):
    store_id: Key
    item_number: ItemNumber
    ordering_day: FlexDate
    delivery_day: FlexDate
    recommended_quantity: Pieces


# API Response Schemas ---------
class Recommendation(BaseModel):
    """One recommended order line, enriched with the item and its price for this day.

    Five fields are nullable. `is_bio` is null for an item that is orderable but has no
    catalog entry. `tags` is null for most items. `purchase_price` and `profit_margin`
    go missing together in the source data (~5% of rows), and `order_cost` derives from
    `purchase_price`, so it is null exactly when that is. The recommendation still
    stands in every one of those cases -- none of them decide orderability.
    """

    item_number: int
    name: str
    category: str
    is_bio: Optional[bool] = None
    tags: Optional[str] = None

    # order is placed in whole pieces; stock is measured, so it stays fractional.
    current_inventory: float
    recommended_quantity: int
    delivery_day: date

    # price differ from items vs orderable_items
    # we use the orderable_items price if it exists
    purchase_price: Optional[float] = None
    suggested_retail_price: float
    profit_margin: Optional[float] = None
    # recommended_quantity * purchase_price: what placing this line costs.
    order_cost: Optional[float] = None

class Metadata(BaseModel):
    file_name: str
    rows_processed: int
    rows_inserted: int
    # flags: list[FlagCount] = [] Out of scope for now

class RecommendationResponse(BaseModel):
    """Response schema for the get /stores/{store_id}/recommendations endpoint"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "store_id": "store_a",
                "date": "2026-01-01",
                "count": 2,
                "recommendations": [
                    {
                        "item_number": 1023,
                        "name": "Papaya",
                        "category": "fruits",
                        "is_bio": False,
                        "tags": "on_sale",
                        "current_inventory": 50,
                        "recommended_quantity": 100,
                        "delivery_day": "2026-01-02",
                        "purchase_price": 1.35,
                        "suggested_retail_price": 2.49,
                        "profit_margin": 0.4578,
                        "order_cost": 135.0
                    },
                    {
                        "item_number": 1028,
                        "name": "Cucumber",
                        "category": "vegetables",
                        "is_bio": True,
                        "tags": "price_change",
                        "current_inventory": 30,
                        "recommended_quantity": 80,
                        "delivery_day": "2026-01-02",
                        "purchase_price": 0.31,
                        "suggested_retail_price": 0.59,
                        "profit_margin": 0.4746,
                        "order_cost": 24.8
                    }
                ]
            }
        }
    )

    store_id: str
    date: date
    count: int
    recommendations: list[Recommendation]


class UploadResponse(BaseModel):
    """Response schema for the post /load/{data_type} endpoints"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Inventory uploaded successfully.",
                "metadata": {
                    "file_name": "inventory.csv",
                    "rows_processed": 100,
                    "rows_inserted": 98,
                }
            }
        }
    )

    status: str
    message: str
    metadata: Optional[Metadata] = None