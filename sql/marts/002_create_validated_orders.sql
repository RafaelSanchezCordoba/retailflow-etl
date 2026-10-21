-- Parses staging.orders' deliberately-TEXT columns (order_timestamp,
-- unit_price -- see sql/staging/001_create_orders.sql) and flags each row
-- valid/invalid for fact_sales. Postgres 16 has no TRY_CAST, so a regex
-- shape-check gates every CAST that could otherwise raise mid-query.
--
-- Hard-invalid (excluded from fact_sales, routed to fact_sales_rejects):
-- null/blank country, non-positive or unparseable quantity/price, an
-- unparseable timestamp, an order_status outside the known set, or a
-- currency with no matching staging.fx_rates row for that date (Frankfurter
-- doesn't cover it -- e.g. the generator's injected "XXX" -- so no EUR
-- amount can be computed at all).
--
-- Soft-invalid (kept in fact_sales, product attributes/margin just null):
-- a product_id with no source.products match. The sale still happened; only
-- the product breakdown and margin are unknown for that line.
CREATE OR REPLACE VIEW mart.v_orders_validated AS
WITH parsed AS (
    SELECT
        o.*,
        CASE WHEN o.order_timestamp ~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
             THEN o.order_timestamp::timestamptz END AS parsed_timestamp,
        CASE WHEN o.unit_price ~ '^[0-9]+(\.[0-9]+)?$'
             THEN o.unit_price::numeric END AS parsed_unit_price
    FROM staging.orders o
)
SELECT
    p.order_id,
    p.order_line_id,
    p.customer_country,
    p.product_id,
    p.quantity,
    p.currency,
    p.order_status,
    p.parsed_timestamp,
    p.parsed_unit_price,
    fx.rate AS fx_rate,
    pr.product_name,
    pr.category,
    pr.unit_cost,
    (
        p.customer_country IS NOT NULL AND p.customer_country <> ''
        AND p.quantity IS NOT NULL AND p.quantity > 0
        AND p.parsed_unit_price IS NOT NULL AND p.parsed_unit_price > 0
        AND p.parsed_timestamp IS NOT NULL
        AND p.order_status IN ('completed', 'cancelled', 'refunded')
        AND fx.rate IS NOT NULL
    ) AS is_valid,
    CASE
        WHEN p.customer_country IS NULL OR p.customer_country = '' THEN 'null_country'
        WHEN p.quantity IS NULL OR p.quantity <= 0 THEN 'invalid_quantity'
        WHEN p.parsed_unit_price IS NULL OR p.parsed_unit_price <= 0 THEN 'invalid_unit_price'
        WHEN p.parsed_timestamp IS NULL THEN 'invalid_timestamp'
        WHEN p.order_status NOT IN ('completed', 'cancelled', 'refunded')
            THEN 'invalid_order_status'
        WHEN fx.rate IS NULL THEN 'unresolvable_currency'
    END AS reject_reason
FROM parsed p
LEFT JOIN staging.fx_rates fx
    ON fx.currency = p.currency AND fx.rate_date = p.parsed_timestamp::date
LEFT JOIN source.products pr
    ON pr.product_id = p.product_id;
