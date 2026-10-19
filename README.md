# RetailFlow — End-to-End ETL/ELT Pipeline

> **Status: work in progress (Stage 1 of 8).** Nothing is runnable yet beyond the test
> suite. This README grows with each stage; see the roadmap below for what exists today.

RetailFlow is a fictional European e-commerce retailer. This project builds the data
pipeline that consolidates its sales data — CSV order files, an external FX-rate API and
an operational PostgreSQL catalog — into analytical tables reporting revenue, margin,
product demand and sales by country, all in EUR.

It is a portfolio project: the goal is a reproducible pipeline whose architectural
decisions can be explained and defended, not maximum technology coverage.

## Planned architecture

Python handles extraction, standardization and validation. Raw snapshots land in S3.
Typed data loads into PostgreSQL staging, and analytical transformations run as SQL in
PostgreSQL — a hybrid ETL/ELT split. Apache Airflow orchestrates; Terraform provisions
the AWS side; GitHub Actions runs the checks.

The core pipeline is intended to run locally without AWS credentials; the cloud steps
skip cleanly when unconfigured.

## Setup

Requires Python 3.11 and (from Stage 3 onwards) Docker. Verified on macOS Intel only.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Checks

```bash
pytest      # test suite
ruff check .
```

## Roadmap

| Stage | Scope | Status |
|---|---|---|
| 1 | Environment & project skeleton | in progress |
| 2 | Python + PostgreSQL CSV ingestion | not started |
| 3 | Apache Airflow orchestration | not started |
| 4 | AWS S3 + Terraform | not started |
| 5 | Three sources + SQL marts | not started |
| 6 | Hardening + CI | not started |
| 7 | Power BI + portfolio writeup | not started |
| 8 | Optional Snowflake warehouse | not started |

## Decisions

Non-trivial choices are recorded in [`docs/decisions/`](docs/decisions/).
