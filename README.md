# RetailFlow — End-to-End ETL/ELT Pipeline

> **Status: Stages 1–6 of 8 complete.** Core pipeline runs end-to-end locally, with
> automated tests and green CI. Stage 7 (Power BI + portfolio writeup) is in progress;
> Stage 8 (optional Snowflake) not started.

RetailFlow is a fictional European e-commerce retailer. This project builds the data
pipeline that consolidates its sales data — CSV order files, an external FX-rate API and
an operational PostgreSQL catalog — into analytical tables reporting revenue, margin,
product demand and sales by country, all in EUR.

It is a portfolio project: the goal is a reproducible pipeline whose architectural
decisions can be explained and defended, not maximum technology coverage.

## Architecture

Python handles extraction, standardization and validation. Raw snapshots land in S3.
Typed data loads into PostgreSQL staging, and analytical transformations run as SQL
views in PostgreSQL `mart` — a hybrid ETL/ELT split. Apache Airflow orchestrates (three
independent, date-partitioned tasks); Terraform provisions the AWS side; GitHub Actions
runs lint/test/DAG-import/Terraform checks on every push, no cloud credentials required.

The core pipeline runs locally with **no AWS credentials** — only the S3 raw-snapshot
task needs them; every other task (orders load, FX rates, SQL marts) works without AWS.

## Setup

Verified on macOS (Intel/Darwin x86_64). Requires Python 3.11, Docker, Docker Compose.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# edit .env: set a real POSTGRES_PASSWORD; generate AIRFLOW_FERNET_KEY and
# AIRFLOW_JWT_SECRET with the one-liners commented in .env.example.
# Leave the AWS_* vars untouched to skip the S3 step (it fails that one task only).

docker compose up -d
docker compose ps   # wait until postgres, airflow-postgres and airflow-* are "healthy"
```

Airflow UI: http://localhost:8080 (user/password from `_AIRFLOW_WWW_USER_USERNAME` /
`_AIRFLOW_WWW_USER_PASSWORD` in `.env`).

## Running the pipeline

Seed reference data once (idempotent, safe to rerun):

```bash
python scripts/seed_catalog.py        # source.products, 20 SKUs
python scripts/generate_sample_orders.py   # sample order CSVs into data/samples/orders/
```

In the Airflow UI, unpause `retailflow_daily` and trigger a run for a logical date that
has a sample CSV (`data/samples/orders/orders_<date>.csv`). Three independent tasks run:
`load_orders` (CSV → `staging.orders`), `upload_raw_snapshot` (CSV → S3, skipped/failing
alone if AWS isn't configured), `load_fx_rates` (Frankfurter API → `staging.fx_rates`).
Rerunning the same logical date is idempotent — zero new rows, confirmed via
`skipped_duplicate` counts in the task logs.

## Checks

```bash
pytest          # unit + integration (integration tests skip cleanly without live services)
ruff check .
```

Same checks run in GitHub Actions on every push — see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml) (three jobs: lint-test,
dag-import, terraform fmt/validate; no cloud credentials needed).

## Sample queries

Against the live container (`docker compose exec postgres psql -U retailflow -d retailflow`):

```sql
-- Net EUR sales and margin by country, completed orders only
SELECT customer_country,
       SUM(net_amount_eur) AS net_sales_eur,
       SUM(margin_eur)     AS margin_eur
FROM mart.fact_sales
WHERE order_status = 'completed'
GROUP BY customer_country
ORDER BY net_sales_eur DESC;

-- Data-quality breakdown: why rows were rejected
SELECT reject_reason, count(*) FROM mart.fact_sales_rejects GROUP BY reject_reason;

-- Dedup proof: one row per order_line_id, no duplicates survive the loader
SELECT count(*), count(DISTINCT order_line_id) FROM staging.orders;
```

More in [`sql/staging/verify_orders.sql`](sql/staging/verify_orders.sql).

## Tests

- `tests/unit/`: sample-data generator determinism and shape, FX-rate module (mocked
  HTTP, no network).
- `tests/integration/`: loader idempotency, S3 upload/replay, and
  `mart.fact_sales` / `fact_sales_rejects` data-quality coverage — one case per
  reject reason — all against real local services (skip cleanly if unavailable).

## Limitations

- Terraform state is local (gitignored), not remote-backed — a solo-developer
  tradeoff, see [`docs/decisions/0002-terraform-local-state.md`](docs/decisions/0002-terraform-local-state.md).
  Not suitable as-is for a multi-developer team.
- This Docker Compose stack is a local development setup, not a production deployment.
- No `dim_country` table — `customer_country` carries no attributes beyond the ISO
  code, so it stays a degenerate dimension on `fact_sales` rather than an empty table.

## Roadmap

| Stage | Scope | Status |
|---|---|---|
| 1 | Environment & project skeleton | done |
| 2 | Python + PostgreSQL CSV ingestion | done |
| 3 | Apache Airflow orchestration | done |
| 4 | AWS S3 + Terraform | done |
| 5 | Three sources + SQL marts | done |
| 6 | Hardening + CI | done |
| 7 | Power BI + portfolio writeup | in progress |
| 8 | Optional Snowflake warehouse | not started |

## Decisions

Non-trivial choices are recorded in [`docs/decisions/`](docs/decisions/).
