-- Operational catalog: one row per SKU. Mirrors a simulated upstream OLTP
-- product table. unit_cost is stored directly in EUR (not the order's
-- transaction currency) so margin = net EUR sales - unit_cost needs no
-- extra FX step on the cost side.
CREATE TABLE IF NOT EXISTS source.products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_cost NUMERIC(10, 2) NOT NULL
);
