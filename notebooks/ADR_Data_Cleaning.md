# ADR: Data Cleaning Summary (per table)

Design Decisions for ingestion layer's cleaning procces.

## items.csv (50 rows, cleanest file)
| Problem | Fix |
|---|---|
| `category` casing (3 rows) | normalize -> `Fruits` / `Vegetables` |
| `name` trailing whitespace (4 rows) | strip |

## inventory.csv (25,868 rows)
| Problem | Fix |
|---|---|
| `store_id` casing/whitespace (8 variants instead of 2) | strip + lowercase -> `store_a` / `store_b` |
| Mixed date formats, ISO vs `DD/MM/YYYY` (3.1%) | parse both -> normalize to ISO `YYYY-MM-DD` |
| Quantity outliers (1,150 rows > 1,000, up to 6,801) | **keep, flag**, not ours to correct, log for monitoring |

## orderable_items.csv (25,200 rows, most complex file)
| Problem | Fix |
|---|---|
| `store_id` casing/whitespace | strip + lowercase |
| `category` casing (5.7%) | normalize -> `Fruits` / `Vegetables` |
| `tags` casing/whitespace (0.3%) | normalize -> `new` / `price_change` / `on_sale` |
| Trailing comma / 10th field which dne (240 rows) | parse the extra empty field **don't drop the row!** |
| `purchase_price` + `profit_margin` always co-missing (5.2%) | **keep, nullable**, not required for orderability |

This table is also the **validity gate**: a recommendation is only served if its
`(store_id, item_number, day)` exists here (INNER JOIN). 
> This is why codes **9901–9903** never reach the API, they're never marked orderable.

## order_recommendations.csv (25,627 rows)
| Problem | Fix |
|---|---|
| `store_id` casing/whitespace | strip + lowercase |
| `item_number` float-encoding, e.g. `"1001.0"` (11.3%) | strip -> canonical int string |
| Negative `recommended_quantity` (2.0%, 515 rows) | **clamp to 0** -> fail-safe, count as anomaly |
| Extreme quantity outliers (7 rows, up to 1,939) | **keep, flag?** -> no evidence they're wrong, log for monitoring |
| Special codes 9901–9903 (332 rows) | **excluded** by the orderable_items INNER JOIN (business rule) |
| Ghost item 1099 (orderable, missing from `items.csv`) | **keep, served** -> LEFT JOIN to catalog, fallback name? = raw `item_number`, log? catalog-gap warning |

## Net effect
`/recommendations` always returns normalized `store_id` / `item_number` / `day`, non-negative quantities, and reports every fix/clamp/exclusion as a count in the load response nothing silently vanishes, note for 9901–9903 items.
