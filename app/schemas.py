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
    item_number: int
    name: str
    category: str
    # An order is placed in whole pieces; stock is measured, so it stays fractional.
    current_inventory: float
    recommended_quantity: int
    delivery_day: date

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
                        "current_inventory": 50,
                        "recommended_quantity": 100,
                        "delivery_day": "2026-01-02"
                    },
                    {
                        "item_number": 1028,
                        "name": "Cucumber",
                        "category": "vegetables",
                        "current_inventory": 30,
                        "recommended_quantity": 80,
                        "delivery_day": "2026-01-02"
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