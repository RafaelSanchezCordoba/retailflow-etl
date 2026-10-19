CREATE TABLE staging.orders (
    order_id          TEXT NOT NULL,
    order_line_id     TEXT PRIMARY KEY,
    order_timestamp   TEXT,
    customer_country  TEXT,
    product_id        TEXT,
    quantity          INTEGER,
    unit_price        TEXT,
    currency          TEXT,
    order_status      TEXT,
    loaded_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);