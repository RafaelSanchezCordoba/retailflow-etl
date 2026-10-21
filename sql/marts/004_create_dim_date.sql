-- Calendar dimension bounded by the observed fact_sales date range -- no
-- separate refresh step, no unnecessary full-years-ahead padding.
-- dim_country is deliberately skipped: customer_country carries no
-- attributes beyond the ISO code itself (no name/region data anywhere in
-- the contract), so it stays a degenerate dimension directly on fact_sales.
CREATE OR REPLACE VIEW mart.dim_date AS
SELECT
    d::date AS date,
    EXTRACT(YEAR FROM d)::int AS year,
    EXTRACT(MONTH FROM d)::int AS month,
    EXTRACT(QUARTER FROM d)::int AS quarter,
    TRIM(TO_CHAR(d, 'Day')) AS day_name,
    EXTRACT(ISODOW FROM d) IN (6, 7) AS is_weekend
FROM generate_series(
    (SELECT MIN(order_date) FROM mart.fact_sales),
    (SELECT MAX(order_date) FROM mart.fact_sales),
    interval '1 day'
) AS d;
