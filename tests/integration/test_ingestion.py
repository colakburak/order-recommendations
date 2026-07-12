from tests.conftest import ITEMS, upload


def test_clean_upload_inserts_every_row(client):
    response = upload(client, "items", *ITEMS)

    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert metadata["rows_processed"] == 3
    assert metadata["rows_inserted"] == 3
    assert metadata["details"] == {}


def test_upload_reports_what_it_fixed_and_what_it_dropped(client):
    response = upload(
        client,
        "recommendations",
        "store_id,item_number,ordering_day,delivery_day,recommended_quantity",
        "store_a,1001,2024-01-01,2024-01-02,10",
        # trailing comma: the named fields still line up, so the row is kept
        "store_a,1002,2024-01-01,2024-01-02,5,",
        # an unquoted comma shifted everything after it: unknowable, so the row goes
        "store_a,1003,2024-01-01,2024-01-02,7,junk",
        # a negative order is clamped rather than dropped
        "store_a,1004,2024-01-01,2024-01-02,-5",
        # unparseable item number: pydantic rejects it and the loader drops the row
        "store_a,abc,2024-01-01,2024-01-02,9",
    )

    metadata = response.json()["metadata"]
    assert metadata["rows_processed"] == 5
    assert metadata["rows_inserted"] == 3
    assert metadata["details"] == {"trailing_comma_fixed": 1, "quantity_clamped": 1}


def test_missing_required_column_is_rejected(client):
    response = upload(
        client,
        "items",
        "item_number,category,is_bio,purchase_price,suggested_retail_price",
        "1001,fruits,false,1.30,2.49",
    )

    assert response.status_code == 422
    assert "missing required columns: name" in response.json()["detail"]


def test_reupload_replaces_the_scope_it_covers(seeded):
    # An upload is the full picture for its (store_id, ordering_day), so a row dropped
    # from a re-upload must disappear rather than linger.
    upload(
        seeded,
        "recommendations",
        "store_id,item_number,ordering_day,delivery_day,recommended_quantity",
        "store_a,1001,2024-01-01,2024-01-02,99",
    )

    body = seeded.get("/stores/store_a/recommendations", params={"date": "2024-01-01"}).json()

    assert body["count"] == 1
    assert body["recommendations"][0]["recommended_quantity"] == 99
