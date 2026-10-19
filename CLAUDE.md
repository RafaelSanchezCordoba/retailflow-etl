# RetailFlow — End-to-End Data Engineering Pipeline

> Project instructions for Claude Code. Treat this document as the source of truth for the project, subject to explicit user decisions. Read it before making changes.

## 1. Project purpose

Build a **credible, reproducible and demonstrable data-engineering portfolio project** from scratch. The project must prove hands-on competence in **Python, SQL, Apache Airflow, Docker Compose, PostgreSQL, AWS S3, Terraform, automated testing and CI**, plus a lightweight **Power BI** report.

This is a learning project aimed at technical interviews. Favor understandable, justified architectural decisions over maximal complexity. It must be possible to run the core system **locally without AWS credentials or Snowflake**, using a clearly documented local-only mode or a graceful cloud-step skip. Never represent a local development Compose setup as production-ready.

**Project name:** RetailFlow — End-to-End ETL/ELT Pipeline  
**Primary environment:** macOS (Intel, Darwin x86_64) with zsh, Docker Desktop/Compose and Git. Repository lives at `~/Develop/retailflow-etl` — deliberately **outside iCloud Drive**, because Docker bind mounts and PostgreSQL data directories inside iCloud sync cause file-locking and partial-sync corruption. Prefer cross-platform code; Windows PowerShell equivalents may be documented but must be marked **unverified** unless actually executed on Windows.  
**Working language:** Communicate with the user **exclusively in English** for all explanations, questions, troubleshooting, step-by-step instructions, and progress updates. Write repository names, code, comments, commit messages, README, and technical documentation in **English** as well. Do not switch to Spanish unless the user explicitly requests it.  
**GitHub repository:** To be created by the user; do not invent its URL.

## 2. Business case and sources

RetailFlow is a fictional European e-commerce retailer. Data is spread across sales CSVs, an external FX-rate API and an operational relational database. The pipeline consolidates it to analyze revenue, margin, product demand and sales by country in EUR.

### Sources

1. **Orders (CSV):** reproducible synthetic, non-sensitive transactional files arriving by date. Example fields: `order_id`, `order_line_id`, `order_timestamp`, `customer_country`, `product_id`, `quantity`, `unit_price`, `currency`, `order_status`. Support different currencies and controlled edge cases (duplicates, nulls, invalid values, missing product IDs). Define contract and seed before implementing loaders; no real customer data.
2. **FX rates (Frankfurter API):** public exchange-rate API (https://frankfurter.dev/). Fetch rates to EUR for the actual transaction date; define treatment of weekends/bank holidays, rate availability and failed requests. Cache/persist source payloads for reproducibility, and avoid making tests depend on a live API. Validate current API endpoints against official documentation when implementing.
3. **Product catalog and inventory (PostgreSQL):** simulated operational tables containing SKU, product metadata, unit costs, categories and possibly stock movements. Use a **logically separate operational schema/database** and analytics schema/database; do not mix operational writes with analytical transforms. Include reproducible seed scripts.

### Expected analytical outputs

- `fact_sales` at **one row per valid order line** (define treatment of cancelled/refunded orders).
- Dimensions such as `dim_product`, `dim_date`, `dim_country` as appropriate; do not create unnecessary dimensions.
- Metrics: gross/net sales in EUR with documented assumptions, units, approximate gross margin where cost is known, orders over time, products and country breakdown.
- Explicitly distinguish raw received amounts, currency conversion, and business-rule deductions. No invented accounting rules.

## 3. Architecture and responsibilities

```text
           Orders CSV          Frankfurter REST API       PostgreSQL OLTP catalog
                \                     |                         /
                 \                    |                        /
                  +------------ Apache Airflow ----------------+
                               | orchestrates
                               v
                     Python extraction/validation
                        |                |
                        v                v
                  AWS S3 raw         PostgreSQL staging
                 (immutable-ish)            |
                        |                  v
                        +----replay----> SQL transformations
                                           |
                                           v
                                    PostgreSQL marts
                                           |
                                           v
                                        Power BI

Terraform manages AWS resources; GitHub Actions performs CI checks.
```

**Key separation:**
- **S3:** object storage/data lake *raw zone* for source snapshots and replay/auditing. Use useful object paths such as `raw/orders/ingestion_date=YYYY-MM-DD/...` and ingestion metadata; never put credentials or PII into object names. Consider versioning, encryption, blocking public access and lifecycle/cost policy. S3 is **not** a substitute for relational querying.
- **PostgreSQL:** separate schemas (e.g. `source`, `staging`, `mart`; Airflow metadata isolated) for operational inputs, typed loading, constraints, SQL transformations and BI. Don't store source bytes only in Postgres and pretend that constitutes S3 integration.
- **Airflow:** Python DAGs with explicit dependencies, date/partition-aware processing, retry/timeouts, sensible scheduling, logs and observability. Business logic lives in testable `src/` modules, not monolithic DAG definitions. No networking or heavy work during DAG parse/import. Prefer the officially supported stable Airflow 3 approach and pin mutually compatible versions after checking official docs.
- **Docker Compose:** local services for Airflow and PostgreSQL; volumes, health checks, startup initialization, isolated databases, and clear commands for start/stop/reset. Use official Airflow development references but do not market this Docker Compose deployment as production-grade.
- **Terraform/AWS:** provision minimal S3 and IAM with least privilege. Backend/state approach documented; do not commit secrets or `terraform.tfstate`. Set budgets/alerts prior to consuming cloud resources. Avoid MWAA, Redshift, NAT gateways, always-on EC2, or other cost-intensive services in the baseline.
- **CI:** GitHub Actions runs Ruff, pytest, SQL/contract checks as feasible, Airflow DAG import validation, Terraform formatting and validation (without AWS apply). No cloud secrets required to run pull-request checks.
- **Power BI:** small optional report, focusing on clear metrics and model correctness over appearance. Document how to refresh or provide safe static visuals where licensing prevents a public live demo.

### ETL/ELT choice

Use Python for extraction, standardization and validation; land raw in S3 when enabled, load typed data into PostgreSQL staging, and perform analytical transformations using **SQL** in Postgres. This hybrid ETL/ELT architecture should be explained clearly in the README.

### Snowflake: **stage 8 only**

Do **not** sign up for, deploy, configure or spend Snowflake trial credits until the core pipeline is stable, tested and documented. In stage 8, implement Snowflake as an **optional alternative analytical warehouse** (S3 -> Snowflake staging -> SQL models/marts), preserving PostgreSQL as a working fallback and as operational source/Airflow metadata. Demonstrate `COPY INTO`, warehouse auto-suspend and cost controls. Check current official trial terms at the time of activation; do not assume fixed free credits or duration without checking.

## 4. Nonfunctional acceptance criteria

1. **Idempotence:** rerunning the same partition/date creates no duplicate order lines or double-counting; unique constraints, merge/upsert and checkpoints where appropriate.
2. **Incrementality/backfills:** a parameterized logical execution date; historical replay does not depend on current wall-clock date. Avoid fragile “latest file only” behavior.
3. **Data quality:** schema checks, required fields, referential integrity, duplicate detection, invalid currency/rate errors, quarantine or explicit failure policy. Tests should cover representative bad inputs.
4. **Reliability:** retries, API timeouts/backoff, error logs without sensitive values, task boundaries and state visibility in Airflow.
5. **Security/cost:** AWS permissions scoped narrowly, no credentials committed, `.env.example` with dummy placeholders only, encrypted/private S3 and cloud cost warnings. Terraform plan must be reviewed before apply.
6. **Reproducibility:** pinned dependencies/lockfiles where sensible, deterministic datasets, documented setup on macOS (primary, verified), no hidden manual state.
7. **Observability:** pipeline execution results, counts (received/accepted/rejected), freshness or last-processed watermark, and screenshots/diagrams for portfolio evidence.
8. **Professional documentation:** readable README with problem, scope, architecture, source contracts, setup, operations, trade-offs, sample queries, tests, limitations and roadmap; a short case study and demo recording outline.

## 5. Planned repository structure

This is a target, not a demand to generate empty directories on day one:

```text
retailflow-etl/
├── CLAUDE.md
├── README.md
├── .gitignore
├── .env.example
├── pyproject.toml
├── Dockerfile
├── compose.yaml
├── dags/
│   └── retailflow_daily.py
├── src/retailflow/
│   ├── config.py
│   ├── extract/
│   ├── validate/
│   ├── transform/
│   └── load/
├── sql/
│   ├── source/
│   ├── staging/
│   └── marts/
├── scripts/
│   ├── generate_sample_orders.py
│   └── seed_catalog.py
├── data/
│   └── samples/              # safe, small sample data only
├── tests/
│   ├── unit/
│   └── integration/
├── infrastructure/terraform/
├── .github/workflows/
├── dashboards/
└── docs/
    ├── architecture.md
    ├── decisions/
    └── portfolio-case-study.md
```

Keep naming consistent, modules small, domain contracts explicit and SQL reviewable. For database migrations, use versioned SQL scripts or an appropriate migration tool if warranted.

## 6. Eight-stage implementation roadmap

| Stage | Scope | Completion evidence |
|---|---|---|
| **1. Environment & skeleton** | Inspect installed Python, Docker, Compose, Git and Terraform; choose pinned supported versions; initialize Git repository, minimal docs and Python package | version checks pass, clean commit, basic tests run |
| **2. Python + PostgreSQL CSV ingestion** | Synthetic order generator, isolated Postgres source/staging, schema/contracts, CSV extraction and idempotent loader | reproducible load, SQL verification, duplicate-run test |
| **3. Apache Airflow** | Dockerized Airflow, first DAG using `src/`, scheduling, retries, logs, partition-aware jobs | successful end-to-end DAG run and rerun |
| **4. AWS S3 + Terraform** | Budget alert, private encrypted bucket, least privilege IAM, raw snapshots, credentials handled safely | reviewed `terraform plan`, tested upload/replay, no secrets committed |
| **5. Three sources + SQL marts** | Frankfurter API, catalog/inventory PostgreSQL, historical FX normalization, star-style tables | tested multi-source joins, consistent EUR metrics |
| **6. Hardening + CI** | incrementality/backfills, quarantines, data-quality checks, pytest/Ruff, GitHub Actions and IaC checks | automated green CI, bad-data test scenarios |
| **7. Power BI + portfolio** | compact dashboard, screenshots/diagram, README, architecture rationale, demo script, LinkedIn case study | another engineer can reproduce project from README |
| **8. Optional Snowflake** | activate trial **only now**; S3 stage, loading, analytical SQL, cost controls, Postgres fallback | working Snowflake demonstration and recorded evidence before trial ends |

**Do not skip prerequisites or silently start stage 8.** A stage is complete only after user has executed and verified its acceptance checks.

## 7. How Claude Code must collaborate

- Be a **hands-on mentor and pair engineer**, not an autonomous agent that creates the whole codebase in one pass. User wants to learn and explain each decision.
- Work **one actionable step at a time**. Explain *what, why, exact command/code, expected output, and how to verify*. Stop and request the actual result before continuing. Never assume a command succeeded.
- Environment inspection baseline (zsh, macOS — do not install without a reason):

  ```bash
  python3 --version
  docker --version
  docker compose version
  git --version
  terraform --version
  ```

- After checks, create the initial repository incrementally; propose each substantive architecture decision and record nontrivial choices in `docs/decisions/` when appropriate.
- Prefer official documentation and well-maintained solutions. Check current versions/API compatibility before giving version-specific commands; if web tools are unavailable, clearly identify unverified assumptions.
- Keep stages minimal: **working vertical slices**, never thousands of lines of scaffolding for future stages.
- For every code change: summarize files modified, commands to run, tests executed and any failures; distinguish tests actually run from those only recommended.
- If a tool/command fails, **diagnose it** before changing direction. Never erase user data, force-push, drop databases, destroy Terraform resources or incur cloud costs without explicit confirmation.
- Ask questions only if essential; otherwise use safe defaults and explain them. Never request pasted AWS secret keys or other credentials in chat. Use AWS profiles / environment integrations appropriately.
- Avoid adding Kafka, Spark, Kubernetes, Databricks or other components merely to maximize keyword coverage. Consider them only if a concrete scope need appears.
- Keep assumptions and tradeoffs documented; be precise about what is or isn't implemented.

## 8. Portfolio definition of done

A reviewer should be able to:

1. Understand the business problem and inspect a clear architecture diagram.
2. Start the local stack with documented commands and run a sample DAG.
3. See at least one **successful** automated run with **three data sources** and concrete quality metrics.
4. Run SQL proving deduplication, EUR conversion and meaningful analytical outputs.
5. Inspect real tests, GitHub Actions results, Terraform resources and least-privilege rationale.
6. Access a concise dashboard and screenshots/video without requiring access to paid services.
7. Understand deployment tradeoffs and the optional Snowflake warehouse extension.

---

## 9. Progress log

### Stage 1 — Environment & skeleton (complete, 2026-10-19)

**Step 1.1 — Environment inspection (done, 2026-10-19).** Verified on macOS Darwin 25.3.0 x86_64:

| Tool | Version found | Verdict |
|---|---|---|
| Python | 3.11.8 | OK — supported by Airflow 3 |
| Docker Engine | 20.10.22 | too old — upgraded in Step 1.3 |
| Docker Compose | v2.15.1 | too old — upgraded in Step 1.3 |
| Git | 2.55.0 | OK |
| Terraform | 1.16.4 | OK |

**Step 1.2 — Relocation (done, 2026-10-19).** Repository moved from iCloud Drive to `~/Develop/retailflow-etl`. Rationale recorded in `docs/decisions/0001-local-development-environment.md` (to be written in Step 1.4).

**Step 1.3 — Docker upgrade (done, 2026-10-19).** Docker Desktop upgraded. Verified: Docker Engine **29.9.1**, Docker Compose **v5.6.0**, `docker run --rm hello-world` succeeded (amd64). All five baseline tools now green.

**Step 1.4 — Repository skeleton (done, 2026-10-19).** Created: `.gitignore`, `pyproject.toml` (hatchling, src layout, Python `>=3.11,<3.13`, dev extras pinned to `pytest==9.1.1` / `ruff==0.17.1`), `src/retailflow/__init__.py`, `tests/unit/test_package.py`, `README.md`, `docs/decisions/0001-local-development-environment.md`. Runtime dependencies deliberately empty — added per stage, when first needed. `.env.example` deferred to Stage 2 (no configuration values exist yet).

**Step 1.5 — Acceptance checks (done, 2026-10-19).** Executed by Claude, not the user; all output real:

- `.venv` created on Python 3.11.8, `pip install -e ".[dev]"` succeeded
- `pytest` → `1 passed`
- `ruff check .` → `All checks passed!`
- `git init -b main`, first commit `8b82714 chore: initialize project skeleton` (7 files). `.venv/` and `.claude/settings.local.json` confirmed ignored via `git check-ignore`

Stage 1 acceptance criteria (version checks pass, clean commit, basic tests run) are met.

**Open items carried into later stages:**

1. The `<3.13` upper bound in `requires-python` is an assumption; verify against official Airflow 3 documentation in Stage 3.
2. No GitHub remote exists yet — user must create the repository and `git remote add origin`. Do not invent the URL.

### Stage 2 — Python + PostgreSQL CSV ingestion (complete, 2026-10-19)

**Step 2.1 — Orders CSV contract (done, 2026-10-19).** Contract written at
`docs/contracts/orders_csv.md`. Key decisions, made by user:

- `fact_sales` keeps cancelled/refunded order lines with `order_status` as a column
  (not dropped) — enables a cancellation-rate metric without re-ingesting.
- `order_line_id` is globally unique across the whole dataset (not composite with
  `order_id`) — single-column primary key everywhere.

**Step 2.2 — Sample data generator (done, 2026-10-19).** `scripts/generate_sample_orders.py`
(stdlib only, no new dependency). Deterministic per `(seed, logical_date)`. Injects one of
8 defect types (duplicate line id, null country, missing product id, non-positive
quantity, invalid price, invalid currency, invalid status, invalid timestamp) at a
configurable rate, default 8%. Covered by `tests/unit/test_generate_sample_orders.py`
(6 tests: determinism, column shape, key columns never blank, duplicate injection,
defect list non-empty). Generated 5 days of sample data (40 rows/day) into
`data/samples/orders/` for the repo.

Role split going forward: Claude writes contracts and fixture/generator tooling: user
writes the staging DDL and the loader, with Claude reviewing each piece.

**Step 2.3 — Local Postgres via Docker Compose (done, 2026-10-19).** `compose.yaml`
(single `postgres:16` service, healthcheck, named volume), `sql/init/001_create_schemas.sql`
(creates `source`, `staging`, `mart` schemas on first boot), `.env.example` / `.env`
(dummy-safe placeholders, `.env` gitignored). Verified: `docker compose ps` shows
`healthy`; `\dn` lists all three schemas. User wrote and ran this step.

**Step 2.4 — `staging.orders` table (done, 2026-10-19).** `sql/staging/001_create_orders.sql`,
written by user, reviewed by Claude. `order_line_id` is the sole primary key.
`order_timestamp` and `unit_price` are deliberately `TEXT`, not `TIMESTAMPTZ`/`NUMERIC` —
the generator's injected bad values (`"not-a-timestamp"`, empty price) are not valid
literals for those types, and a typed column would reject the whole row at `INSERT`
instead of letting it land in staging for later inspection. No `NOT NULL`/`CHECK` on
business columns for the same reason; `order_id`/`order_line_id` are `NOT NULL` since the
contract guarantees the generator never leaves those blank. Verified via `\d staging.orders`.

**Step 2.5 — Idempotent loader (done, 2026-10-19).** User asked Claude to take over
this step directly rather than being guided line-by-line. `src/retailflow/load/orders.py`:
reads an orders CSV with `csv.DictReader`, `INSERT ... ON CONFLICT (order_line_id) DO
NOTHING` per row, returns per-file `(read, inserted, skipped_duplicate)` counts — the
received/accepted/rejected observability CLAUDE.md §4.7 asks for. `quantity` cast to
`int` in Python before insert (contract guarantees it's always a valid integer, even in
injected-defect rows). Added `psycopg[binary]==3.3.6` as the one runtime dependency.
`tests/integration/test_load_orders.py` proves idempotency against the real container
(connects via `connection_from_env()`, skips cleanly if Postgres isn't reachable).

**Verified, real output, not assumed:**
- `pytest` → 7 passed (6 unit + 1 integration, against the live container)
- `ruff check .` → clean
- Loader run against all 5 sample files: `TOTAL: read=200 inserted=198 skipped_duplicate=2`
  (the 2 skips are the generator's injected `duplicate_order_line_id` defects)
- Rerun of the same files: `read=200 inserted=0 skipped_duplicate=200` — proves the
  duplicate-run acceptance criterion from CLAUDE.md §6 (Stage 2 row)
- `SELECT count(*) FROM staging.orders` → 198, matching `inserted` exactly

**Role-split note:** Stage 2 started with the user writing Compose/SQL/DDL under
Claude's guidance (Steps 2.3–2.4), then the user explicitly asked Claude to take the
loader step end-to-end to move faster (Step 2.5). Apply per-step, not as a blanket rule
going forward — ask if unclear which mode a new step should use.

**Password rotation note (2026-10-19).** User changed `POSTGRES_PASSWORD` in `.env`
after initial setup (it still held Claude's placeholder). Confirmed `.env` stays
gitignored, so this is config-only, no code change. However the Postgres container's
data volume was already initialized with the old password — `POSTGRES_PASSWORD` only
takes effect on an empty data directory, so editing `.env` alone did not change the
live role's password. Diagnosed via a real TCP+password connection attempt (failed),
not just a local-socket check (which trust-bypasses password auth and would have given
a false pass). Fixed with `ALTER ROLE retailflow WITH PASSWORD '...'` against the
running container, then re-verified the same TCP+password connection succeeds.

**Step 2.6 — SQL verification queries (done, 2026-10-19).** `sql/staging/verify_orders.sql`,
three queries, run against the live container with real output:

1. Dedup proof: `total_rows = distinct_order_line_ids = 198`.
2. Data-quality breakdown: `null_country=2, bad_quantity=2, bad_unit_price=2,
   bad_order_status=0, bad_timestamp=2`. Deliberately excludes `product_id` and
   `currency` — `missing_product_id` injects a syntactically valid but non-existent
   SKU (referential integrity, needs the Stage 5 catalog) and `invalid_currency`
   injects `"XXX"` (shape-valid 3 letters, not a real convertible currency; needs the
   Stage 5 Frankfurter currency list). Checking those two with a regex would have
   silently reported zero defects — caught by cross-checking against raw grep/csv
   counts on the source files before trusting the query.
3. Clean-on-checkable-rules count: `190/198`.

All counts cross-verified against the 5 raw sample CSVs directly (not just trusted
from the query), and reconcile exactly with the generator's 8% injection rate once the
2 pre-insert duplicate skips are included: 2 duplicates + 2 null-country + 2 missing-SKU
+ 2 bad-quantity + 2 bad-price + 4 bad-currency + 0 bad-status + 2 bad-timestamp = 16/200.

**Scope decision (2026-10-19):** Stage 2 stops here. A `source` schema seed
(catalog/inventory) belongs to Stage 5 per the roadmap (§3, §6) — adding it now would
be scaffolding ahead of need. Stage 2 acceptance criteria (reproducible load, SQL
verification, duplicate-run test) are met.

**Next action: Stage 3 — Apache Airflow. Start with environment inspection (confirm
Airflow 3 version/compatibility against official docs, resolving the `requires-python
<3.13` open item from Stage 1) before touching Compose or DAG code.**
