-- Thin pass-through over source.products. A view, not a table: no refresh
-- step needed, always reflects the current catalog.
CREATE OR REPLACE VIEW mart.dim_product AS
SELECT product_id, product_name, category, unit_cost
FROM source.products;
