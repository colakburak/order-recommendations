import pytest


@pytest.fixture
def recommendations(seeded) -> dict[int, dict]:
    response = seeded.get("/stores/store_a/recommendations", params={"date": "2024-01-01"})
    assert response.status_code == 200
    body = response.json()
    return {row["item_number"]: row for row in body["recommendations"]}


def test_only_orderable_items_are_recommended(recommendations):
    # 1099 is orderable without a catalog entry and still stands; 1004 is recommended but
    # not orderable, and 1003 is orderable but not recommended -- neither is served.
    assert sorted(recommendations) == [1001, 1002, 1099]


def test_recommendation_is_enriched_from_the_catalog_and_the_day_price(recommendations):
    assert recommendations[1001] == {
        "item_number": 1001,
        "name": "Papaya",
        "category": "fruits",
        "is_bio": False,
        "tags": "on_sale",
        "current_inventory": 50.5,
        "recommended_quantity": 10,
        "delivery_day": "2024-01-02",
        # the store's price for the day, not the catalog's 1.30
        "purchase_price": 1.35,
        "suggested_retail_price": 2.49,
        "profit_margin": 0.4578,
        "order_cost": 13.5,
    }


def test_item_missing_from_the_catalog_falls_back_to_its_number(recommendations):
    ghost = recommendations[1099]

    assert ghost["name"] == "1099"
    assert ghost["is_bio"] is None
    assert ghost["order_cost"] == 6.0


def test_missing_inventory_and_price_do_not_drop_the_line(recommendations):
    cucumber = recommendations[1002]

    # no inventory snapshot means no stock, not a missing row
    assert cucumber["current_inventory"] == 0.0
    # purchase_price and profit_margin go missing together, and order_cost derives from price
    assert cucumber["purchase_price"] is None
    assert cucumber["profit_margin"] is None
    assert cucumber["order_cost"] is None
    assert cucumber["recommended_quantity"] == 5


def test_a_day_with_nothing_to_order_is_an_empty_list(seeded):
    response = seeded.get("/stores/store_a/recommendations", params={"date": "2024-06-01"})

    assert response.status_code == 200
    assert response.json() == {
        "store_id": "store_a",
        "date": "2024-06-01",
        "count": 0,
        "recommendations": [],
    }
