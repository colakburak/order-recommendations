from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel

from app.models import Base, Inventory, Item, OrderableItem, OrderRecommendation
from app.schemas import InventoryRow, ItemRow, OrderableItemRow, OrderRecommendationRow


@dataclass(frozen=True)
class Dataset:
    """Everything the service needs to know about one CSV.

    Nothing else in the codebase is per-table: the required columns come from `model`,
    the primary key and updatable columns from `table`, and the snapshot an upload
    replaces from `scope`. An empty scope means the dataset is a catalog shared across
    stores and days, so a re-upload deletes nothing.
    """

    row_schema: type[BaseModel]
    table_model: type[Base]
    scope: tuple[str, ...]

    @property
    def required_columns(self) -> set[str]:
        """The columns a CSV must carry. An optional field may be absent entirely."""
        return {name for name, field in self.row_schema.model_fields.items() if field.is_required()}

    @property
    def primary_key(self) -> list[str]:
        return list(self.table_model.__table__.primary_key.columns.keys())

    @property
    def update_columns(self) -> list[str]:
        primary_key = self.primary_key
        return [c for c in self.table_model.__table__.columns.keys() if c not in primary_key]


class DatasetName(str, Enum):
    """The loadable datasets. The values are the `/load/{dataset}` URL segments."""

    items = "items"
    inventory = "inventory"
    orderable_items = "orderable_items"
    recommendations = "recommendations"

    @property
    def label(self) -> str:
        """'orderable_items' -> 'Orderable items', for the upload response message."""
        return self.value.replace("_", " ").capitalize()


DATASETS: dict[DatasetName, Dataset] = {
    DatasetName.items: Dataset(
        ItemRow, Item, scope=()
    ),
    DatasetName.inventory: Dataset(
        InventoryRow, Inventory, scope=("store_id", "day")
    ),
    DatasetName.orderable_items: Dataset(
        OrderableItemRow, OrderableItem, scope=("store_id", "ordering_day")
    ),
    DatasetName.recommendations: Dataset(
        OrderRecommendationRow, OrderRecommendation, scope=("store_id", "ordering_day")
    ),
}
