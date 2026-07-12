from typing import Literal, Optional
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["fruits", "vegetables"]
Tags = Literal["new", "price_change", "on_sale"]

# Post Cleaned Schemas --------------
class ItemRow(BaseModel):
    item_number: int
    name: str
    category: Category
    is_bio: bool
    purchase_price: float
    suggested_retail_price: float

class InventoryRow(BaseModel):
    store_id: str
    item_number: int
    day: date
    quantity: float = Field(allow_inf_nan=False)

class OrderableItemRow(BaseModel):
    store_id: str
    item_number: int
    ordering_day: date
    delivery_day: date
    purchase_price: Optional[float] = None
    suggested_retail_price: float
    profit_margin: Optional[float] = None
    tags: Optional[Tags] = None
    category: Category

class OrderRecommendationRow(BaseModel):
    store_id: str
    item_number: int
    ordering_day: date
    delivery_day: date
    recommended_quantity: int = Field(ge=0)


# API Response Schemas ---------
class Recommendation(BaseModel):
    item_number: int
    name: str
    category: Category
    # An order is placed in whole pieces; stock is measured, so it stays fractional.
    current_inventory: float
    recommended_quantity: int
    delivery_day: date

class FlagCount(BaseModel):
    reason: str
    description: str
    count: int

class Metadata(BaseModel):
    file_name: str
    rows_processed: int
    rows_inserted: int
    rows_skipped: int
    flags: list[FlagCount] = []


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
                "message": "Items data synced successfully.",
                "metadata": {
                    "file_name": "items.csv",
                    "rows_processed": 100,
                    "rows_inserted": 98,
                    "rows_skipped": 2,
                    "flags": []
                }
            }
        }
    )

    status: str
    message: str
    metadata: Optional[Metadata] = None