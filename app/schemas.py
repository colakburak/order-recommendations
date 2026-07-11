from typing import Literal, Optional
from datetime import date

from pydantic import BaseModel

# lowercase, singular, no spaces, no special characters
Category = Literal["fruits", "vegetables"]

# Post Cleaned Schemas
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
    quantity: float

class OrderableItemRow(BaseModel):
    store_id: str
    item_number: int
    ordering_day: date
    delivery_day: date
    purchase_price: float
    suggested_retail_price: float
    profit_margin: float
    tags: Optional[str]
    category: Category

class OrderRecommendationRow(BaseModel):
    store_id: str
    item_number: int
    ordering_day: date
    delivery_day: date
    recommended_quantity: float