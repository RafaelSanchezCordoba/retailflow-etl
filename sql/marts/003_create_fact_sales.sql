-- One row per valid order line (cancelled/refunded kept, per
-- docs/contracts/orders_csv.md). gross_amount_eur is the raw converted
-- amount regardless of status; net_amount_eur zeroes out anything not
-- "completed" -- the only business-rule deduction applied, no invented
-- accounting beyond that. margin_eur is null whenever the product's cost
-- is unknown (unresolved SKU) or the line isn't completed.
CREATE OR REPLACE VIEW mart.fact_sales AS
SELECT
    order_line_id,
    order_id,
    parsed_timestamp::date AS order_date,
    customer_country,
    product_id,
    quantity,
    parsed_unit_price AS unit_price,
    currency,
    order_status,
    fx_rate,
    ROUND(parsed_unit_price * quantity / fx_rate, 2) AS gross_amount_eur,
    ROUND(
        CASE WHEN order_status = 'completed'
             THEN parsed_unit_price * quantity / fx_rate
             ELSE 0 END,
        2
    ) AS net_amount_eur,
    CASE WHEN unit_cost IS NOT NULL AND order_status = 'completed'
         THEN ROUND(parsed_unit_price * quantity / fx_rate - unit_cost * quantity, 2)
    END AS margin_eur
FROM mart.v_orders_validated
WHERE is_valid;

-- Quarantined rows, for the received/accepted/rejected observability
-- CLAUDE.md asks for (section 4.7).
CREATE OR REPLACE VIEW mart.fact_sales_rejects AS
SELECT
    order_line_id, order_id, reject_reason,
    customer_country, product_id, quantity, currency, order_status
FROM mart.v_orders_validated
WHERE NOT is_valid;
