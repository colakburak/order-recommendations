# Order Recommendations

Ingests FreshFlow's daily CSVs and serves per-store order recommendations, enriched with
the item catalog, the store's price for that day, and current stock.

## Quickstart

```sh
make demo
```

Builds the image, starts the container, loads all four CSVs from `data/`, and prints
recommendations for `store_a` on `2024-01-01`. Pick another day with
`make demo STORE=store_b DATE=2024-01-02`. Run `make` on its own to list every target.

Without `make`:

```sh
docker build -t order-rec .
docker run -p 8000:8000 order-rec

curl -X POST -F "file=@data/items.csv"                 localhost:8000/load/items
curl -X POST -F "file=@data/orderable_items.csv"       localhost:8000/load/orderable_items
curl -X POST -F "file=@data/inventory.csv"             localhost:8000/load/inventory
curl -X POST -F "file=@data/order_recommendations.csv" localhost:8000/load/recommendations

curl "localhost:8000/stores/store_a/recommendations?date=2024-01-01"
```

Interactive docs: <http://localhost:8000/docs>.

## Make targets

| Target | Does |
|---|---|
| `make` | List these targets |
| `make demo` | `build` → `run` → `load-data` → `query`, end to end |
| `make build` | Build the Docker image |
| `make run` | Start the container and wait until it answers |
| `make load-data` | Upload all four CSVs from `data/` |
| `make query` | Show recommendations for `$(STORE)` on `$(DATE)` |
| `make logs` | Follow the container logs |
| `make stop` | Stop and remove the container |
| `make test` | Run the test suite |
| `make lint` | Lint with ruff |
| `make dev` | Run the API locally with reload, no Docker |

`STORE`, `DATE`, `PORT`, `IMAGE` and `NAME` are all overridable:
`make query STORE=store_b DATE=2024-01-02`.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /load/{dataset}` | Upload one CSV (multipart). `dataset` is one of `items`, `inventory`, `orderable_items`, `recommendations`. |
| `GET /stores/{store_id}/recommendations?date=YYYY-MM-DD` | The order lines for that store and day. |

Note `order_recommendations.csv` loads at `/load/`**`recommendations`** — the dataset is
named for the table, not the file.

An upload answers with what the loader actually did, so data quality is visible at ingest
rather than discovered later:

```json
{"file_name": "order_recommendations.csv", "rows_processed": 25627,
 "rows_inserted": 25627, "details": {"quantity_clamped": 515}}
```

A recommendation carries everything needed to place the order:

```json
{"item_number": 1001, "name": "Organic Bananas", "category": "fruits", "is_bio": false,
 "tags": null, "current_inventory": 16.4, "recommended_quantity": 18,
 "delivery_day": "2024-01-02", "purchase_price": 0.93, "suggested_retail_price": 1.47,
 "profit_margin": 0.386, "order_cost": 16.74}
```

## Layout

```
app/
  main.py             the two endpoints
  datasets.py         the four datasets: row schema, table, and what a re-upload replaces
  ingestion/          CSV -> validated rows; cleaners.py holds every cleaning rule
  recommendations.py  the read path: recommendations x orderable x items x inventory
  db.py, models.py    SQLite engine and tables
tests/                unit (cleaning rules) and integration (upload -> query round trip)
notebooks/            data exploration and the cleaning ADR
```

## Data decisions

Every cleaning rule and the reasoning behind it is in
[notebooks/ADR_Data_Cleaning.md](notebooks/ADR_Data_Cleaning.md). 

**An upload is the full picture for its scope.** Re-uploading a `(store_id, ordering_day)`
deletes the rows that disappeared from the file instead of leaving them stale. `items` is
a catalog shared across stores and days, so it has no scope and a re-upload deletes
nothing. See `upsert` in [app/db.py](app/db.py).

**Nulls are answers, not errors.** `purchase_price` and `profit_margin` go missing
together in ~5% of rows, and `order_cost` is null exactly when the price is. An item that
is orderable but absent from the catalog is still served, with its number as a fallback
name. None of these decide whether a store can order the item, so none of them drop the
line.

**An order for zero pieces is not an order,** so it is not served. A negative quantity clamps to zero at ingest, and ~2,403 rows arrive as zero already. Both are stored, and the clamp is counted in the upload response, so nothing is lost and the endpoint returns only lines a store would actually put on a purchase order.

## Tests

```sh
make test
```

- `tests/unit` covers the cleaning contract in isolation. 
- `tests/integration` drives the real endpoints against an in-memory database.

## Notes

SQLite, because ~75k rows in a single container does not need anything else. The database
is a file inside the container and starts empty on each run; mount one to keep it
(`docker run -v $(pwd)/db:/data -p 8000:8000 order-rec`, see `APP_DB_PATH`).
