import os

# app.db builds its engine at import time, so the test database has to be chosen
# before anything imports app. pytest loads conftest first, which makes this the spot.
os.environ["APP_DB_PATH"] = ":memory:"

import pytest
from fastapi.testclient import TestClient

from app.db import ENGINE
from app.main import app
from app.models import Base


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """One empty database per test: uploads must not leak between them."""
    Base.metadata.drop_all(ENGINE)
    Base.metadata.create_all(ENGINE)
    yield


def upload(client: TestClient, dataset: str, *lines: str):
    """POST one inline CSV to /load/{dataset}. Real data/*.csv files are ~25k rows."""
    content = "\n".join(lines).encode()
    return client.post(
        f"/load/{dataset}",
        files={"file": (f"{dataset}.csv", content, "text/csv")},
    )


# A store's day, small enough to read: 1001 is a plain item, 1002 has no purchase price,
# 1099 is orderable but missing from the catalog, 1003 is orderable but not recommended,
# and 1004 is recommended but not orderable.
ITEMS = (
    "item_number,name,category,is_bio,purchase_price,suggested_retail_price",
    "1001,Papaya,fruits,false,1.30,2.49",
    "1002,Cucumber,vegetables,true,0.31,0.59",
    "1003,Lemon,fruits,false,0.20,0.45",
)
ORDERABLE_ITEMS = (
    "store_id,item_number,ordering_day,delivery_day,purchase_price,"
    "suggested_retail_price,profit_margin,tags,category",
    "store_a,1001,2024-01-01,2024-01-02,1.35,2.49,0.4578,on_sale,fruits",
    "store_a,1002,2024-01-01,2024-01-02,,0.59,,,vegetables",
    "store_a,1003,2024-01-01,2024-01-02,0.20,0.45,0.55,,fruits",
    "store_a,1099,2024-01-01,2024-01-02,2.00,3.50,0.43,,herbs",
)
RECOMMENDATIONS = (
    "store_id,item_number,ordering_day,delivery_day,recommended_quantity",
    "store_a,1001,2024-01-01,2024-01-02,10",
    "store_a,1002,2024-01-01,2024-01-02,5",
    "store_a,1099,2024-01-01,2024-01-02,3",
    "store_a,1004,2024-01-01,2024-01-02,7",
)
INVENTORY = (
    "store_id,item_number,day,quantity",
    "store_a,1001,2024-01-01,50.5",
)


@pytest.fixture
def seeded(client: TestClient) -> TestClient:
    """All four datasets loaded through the upload endpoint."""
    upload(client, "items", *ITEMS)
    upload(client, "orderable_items", *ORDERABLE_ITEMS)
    upload(client, "recommendations", *RECOMMENDATIONS)
    upload(client, "inventory", *INVENTORY)
    return client
