from datetime import date
from typing import Optional

from sqlalchemy import CheckConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    item_number: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    category: Mapped[str]
    is_bio: Mapped[bool]
    purchase_price: Mapped[float]
    suggested_retail_price: Mapped[float]


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        Index("idx_inventory_store_day", "store_id", "day"),
    )

    store_id: Mapped[str] = mapped_column(primary_key=True)
    item_number: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(primary_key=True)
    quantity: Mapped[float]


class OrderableItem(Base):
    __tablename__ = "orderable_items"
    __table_args__ = (
        Index("idx_orderable_items_store_day", "store_id", "ordering_day"),
    )

    store_id: Mapped[str] = mapped_column(primary_key=True)
    item_number: Mapped[int] = mapped_column(primary_key=True)
    ordering_day: Mapped[date] = mapped_column(primary_key=True)
    delivery_day: Mapped[date]
    purchase_price: Mapped[Optional[float]]
    suggested_retail_price: Mapped[float]
    profit_margin: Mapped[Optional[float]]
    tags: Mapped[Optional[str]]
    category: Mapped[str]


class OrderRecommendation(Base):
    __tablename__ = "order_recommendations"
    __table_args__ = (
        CheckConstraint("recommended_quantity >= 0", name="ck_order_recommendations_qty_nonneg"),
        Index("idx_order_recommendations_store_day", "store_id", "ordering_day"),
    )

    store_id: Mapped[str] = mapped_column(primary_key=True)
    item_number: Mapped[int] = mapped_column(primary_key=True)
    ordering_day: Mapped[date] = mapped_column(primary_key=True)
    delivery_day: Mapped[date]
    recommended_quantity: Mapped[float]
