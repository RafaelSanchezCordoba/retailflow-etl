-- One row per (date, currency): units of currency per 1 EUR, as published by
-- Frankfurter (base=EUR). (rate_date, currency) is the natural key.
CREATE TABLE IF NOT EXISTS staging.fx_rates (
    rate_date DATE NOT NULL,
    currency TEXT NOT NULL,
    rate NUMERIC(14, 6) NOT NULL,
    PRIMARY KEY (rate_date, currency)
);
