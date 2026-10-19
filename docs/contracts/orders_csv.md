# Source contract — Orders CSV

- **Status:** Accepted
- **Date:** 2026-10-19
- **Scope:** shape and content of the orders CSV files as delivered by the (simulated)
  upstream system. This document does not define the accept/quarantine/reject policy
  for bad rows — that validation logic is implemented and documented separately
  (Stage 2/6), against this contract.

## Delivery

One file per day: `orders_YYYY-MM-DD.csv`. The date in the filename is the **logical
date**, not the file's creation time — reprocessing an old date must produce the same
file name and the same rows (no "latest file only" behaviour, per CLAUDE.md §4.2).

## Columns

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `order_id` | string | no | Groups lines of one order. Format `ORD-{logical_date}-{seq}`, e.g. `ORD-20260101-000123`. Not unique per row — shared by every line of the same order. |
| `order_line_id` | string | no | **Primary key, globally unique across the entire dataset** (not just within an order). Format `{order_id}-L{n}`. Chosen deliberately as a single-column key so constraints, upserts and joins never need a composite key. |
| `order_timestamp` | ISO-8601 UTC, e.g. `2026-01-01T13:45:00Z` | no (structurally) | The business timestamp used for FX-rate lookup and date partitioning. |
| `customer_country` | ISO 3166-1 alpha-2 | yes | e.g. `DE`, `FR`, `ES`. Restricted to a fixed set of EU countries in the generator. |
| `product_id` | string | yes | References a catalog SKU, e.g. `SKU-0007`. May point to a SKU that does not exist in the catalog (injected edge case) — that is a referential-integrity failure, not a CSV-parsing failure. |
| `quantity` | integer | yes | Expected `>= 1`. Zero/negative values are an injected edge case. |
| `unit_price` | decimal, in `currency` | yes | Expected `> 0`. Zero/negative/null values are an injected edge case. |
| `currency` | ISO 4217 | yes | Expected to be a currency the FX source (Frankfurter) can convert to EUR. An unsupported/bogus code is an injected edge case. Exact supported-currency list to be re-checked against the live Frankfurter `/currencies` endpoint in Stage 5 — **not yet verified**. |
| `order_status` | enum string | yes | One of `completed`, `cancelled`, `refunded`. Anything else is an injected edge case. |

`order_id` and `order_line_id` are the only columns the generator guarantees are always
present and well-formed. Every other column can carry a deliberately bad value — if the
identifying columns themselves could be null, a bad row could not even be logged or
quarantined by key.

## `fact_sales` treatment of `order_status`

Decision: **keep every valid order line in `fact_sales`, status included as a column.**
Rows are not dropped by status. Revenue metrics filter `WHERE order_status = 'completed'`;
the same table also supports a cancellation-rate query (`cancelled or refunded` ÷ total)
without a second table. Rejected because of dropping: it would make a legitimate
business metric (cancellation rate) impossible to compute later without re-ingesting.

## Deliberately injected edge cases

The generator (`scripts/generate_sample_orders.py`) injects exactly one defect per
affected row, deterministically, at a configurable rate (default 8%):

| Defect | What it tests |
|---|---|
| `duplicate_order_line_id` | Loader idempotency / primary-key conflict handling |
| `null_customer_country` | Nullable-field handling in marts (e.g. `dim_country` "unknown" bucket) |
| `missing_product_id` | Referential integrity against the catalog |
| `non_positive_quantity` | Business-rule validation (quantity must be ≥ 1) |
| `invalid_unit_price` | Business-rule validation (price must be > 0, not null) |
| `invalid_currency` | FX lookup failure handling |
| `invalid_order_status` | Enum validation |
| `invalid_timestamp` | Parse-failure handling, independent of the above |

All injected rows are still syntactically valid CSV (correct column count, parseable as
text) — they violate business rules, not CSV syntax. Malformed CSV syntax itself
(wrong column count, broken quoting) is not simulated; it is not a realistic failure
mode for a system that writes its own CSVs.

## Open items

1. Supported-currency set is assumed, not verified against the live Frankfurter API —
   revisit in Stage 5.
2. Catalog SKU range (`SKU-0001`–`SKU-0020`) is a placeholder fixed list in the
   generator until Stage 5 builds the real PostgreSQL catalog with a seed script.
