-- Verification queries for staging.orders.
-- Run manually (psql, DBeaver, etc.) after a loader run. Not part of the
-- idempotent-load pytest suite (tests/integration/test_load_orders.py) --
-- this file is the human-readable SQL evidence referenced by CLAUDE.md
-- section 8.4 ("Run SQL proving deduplication... and meaningful analytical
-- outputs").

-- 1. Deduplication proof: every row has a unique order_line_id.
-- total_rows and distinct_order_line_ids must be equal. They are equal by
-- construction (order_line_id is PRIMARY KEY, so Postgres physically cannot
-- store a duplicate), but this query is the auditable evidence of that fact
-- for anyone reviewing the table without reading the DDL.
SELECT
    count(*)                       AS total_rows,
    count(DISTINCT order_line_id)  AS distinct_order_line_ids
FROM staging.orders;

-- 2. Data-quality breakdown: how many landed rows violate each business
-- rule from docs/contracts/orders_csv.md. These rows are NOT rejected at
-- load time (staging is deliberately permissive, see sql/staging/001_create_orders.sql) --
-- this is the observability CLAUDE.md section 4.3/4.7 asks for: visibility
-- into what's wrong with the data, not enforcement.
-- Two columns can't be fully validated yet and are deliberately left out of
-- this query rather than faked:
--   product_id  - "missing_product_id" injects a syntactically valid but
--                  non-existent SKU (SKU-9999), which is a referential
--                  integrity failure against the catalog. No catalog table
--                  exists until Stage 5.
--   currency    - "invalid_currency" injects "XXX", which is 3 uppercase
--                  letters: shape-valid, but not a currency Frankfurter can
--                  convert to EUR. Real validation needs the Frankfurter
--                  currency list (Stage 5), not a regex.
SELECT
    count(*)                                                        AS total_rows,
    count(*) FILTER (
        WHERE customer_country IS NULL OR customer_country = ''
    )                                                                AS null_country,
    count(*) FILTER (WHERE quantity IS NULL OR quantity < 1)         AS bad_quantity,
    count(*) FILTER (
        WHERE unit_price IS NULL
           OR unit_price !~ '^[0-9]+(\.[0-9]+)?$'
           OR unit_price::numeric <= 0
    )                                                                AS bad_unit_price,
    count(*) FILTER (
        WHERE order_status IS NULL
           OR order_status NOT IN ('completed', 'cancelled', 'refunded')
    )                                                                AS bad_order_status,
    count(*) FILTER (
        WHERE order_timestamp !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
    )                                                                AS bad_timestamp
FROM staging.orders;

-- 3. Rows that are clean on every business rule checkable at this stage
-- (excludes product_id / currency for the reasons given in query 2) -- the
-- set a mart transformation could safely use as-is today, versus the set
-- that needs an explicit decision (quarantine, default, or exclude) once
-- Stage 5 adds the catalog and Frankfurter currency list.
SELECT
    count(*) FILTER (
        WHERE (customer_country IS NOT NULL AND customer_country != '')
          AND quantity >= 1
          AND unit_price ~ '^[0-9]+(\.[0-9]+)?$' AND unit_price::numeric > 0
          AND order_status IN ('completed', 'cancelled', 'refunded')
          AND order_timestamp ~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
    ) AS clean_rows,
    count(*) AS total_rows
FROM staging.orders;
