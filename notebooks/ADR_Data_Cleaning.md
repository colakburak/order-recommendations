# ADR: Data Cleaning Summary (per table)

Design Decisions for ingestion layer's cleaning procces.

Two rules are the same for every file, so they are applied to every cell and are not
repeated per table below: **strip whitespace**, and **read a blank cell as missing**.
A missing value is then only a problem if the column is required.

## items.csv (50 rows, cleanest file)
| Problem | Fix |
|---|---|
| `category` casing (3 rows) | lowercase -> `fruits` / `vegetables` |
| `name` trailing whitespace (4 rows) | strip |

## inventory.csv (25,868 rows)
| Problem | Fix |
|---|---|
| `store_id` casing/whitespace (8 variants instead of 2) | strip + lowercase -> `store_a` / `store_b` |
| Mixed date formats, ISO vs `DD/MM/YYYY` (3.1%) | parse both -> normalize to ISO `YYYY-MM-DD` |
| Quantity outliers (1,150 rows > 1,000, up to 6,801) | Do nothing |
| Fractional quantity | **Keep**. Stock is measured, not ordered -- not ours to round |

## orderable_items.csv (25,200 rows, most complex file)
| Problem | Fix |
|---|---|
| `store_id` casing/whitespace | strip + lowercase |
| `category` casing (5.7%) | lowercase |
| `tags` casing/whitespace (0.3%) | strip + lowercase |
| Trailing comma / 10th field which dne (240 rows) | **Keep the row.** The surplus field is blank in all 240, so the named fields are still aligned: drop the surplus, keep the row. A surplus *with content* means an unquoted comma shifted every field after it -- unknowable which, so **that** row we drop |
| `purchase_price` + `profit_margin` always co-missing (5.2%) | **keep, nullable**, not required for orderability |


## order_recommendations.csv (25,627 rows)
| Problem | Fix |
|---|---|
| `store_id` casing/whitespace | strip + lowercase |
| `item_number` float-encoding, e.g. `"1001.0"` (11.3%) | strip -> canonical int string |
| Negative `recommended_quantity` (2.0%, 515 rows) | **clamp to 0** |
| Fractional `recommended_quantity` | **round up**. An order is placed in whole pieces, and this one *is* ours to fix |
| Extreme quantity outliers (7 rows, up to 1,939) | Do nothing|
| Special codes 9901–9903 (332 rows) | do nothing |
| Ghost item 1099 (orderable, missing from `items.csv`) | We only clean do nothing |

## Not enumerated

`category` and `tags` are lowercased, not matched against a fixed list of known values.
A category or tag we have not seen before is loaded as-is rather than nulled, so adding
one upstream does not need a code change here -- and `fruit` vs `fruits` is not a
distinction we are in a position to settle.
