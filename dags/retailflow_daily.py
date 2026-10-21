"""Daily DAG: load one logical date's orders CSV into staging.orders, upload
its raw snapshot to S3, and load that date's FX rates into staging.fx_rates.

Business logic lives in src/retailflow/load/orders.py (CLAUDE.md section 3) --
this file only wires Airflow scheduling, retries and logging around it.

catchup=False: the DAG is created paused and must be triggered manually per
date (UI or `airflow dags backfill`). The file path is built from the run's
logical date (`ds`), never wall-clock "today" -- a backfill for an old date
reads that date's file regardless of when it is actually run (CLAUDE.md
section 4.2).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow.sdk import dag, task

ORDERS_DIR = Path("/opt/airflow/data/samples/orders")
FX_CACHE_DIR = Path("/opt/airflow/data/cache/fx_rates")


@dag(
    dag_id="retailflow_daily",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=1)},
    tags=["retailflow", "stage-5"],
)
def retailflow_daily():
    @task
    def load_orders(*, ds: str) -> dict:
        from retailflow.load.orders import connection_from_env, load_file

        path = ORDERS_DIR / f"orders_{ds}.csv"
        if not path.exists():
            raise FileNotFoundError(f"No orders file for logical date {ds}: {path}")

        with connection_from_env() as conn:
            result = load_file(path, conn)

        print(
            f"{path.name}: read={result.read} inserted={result.inserted} "
            f"skipped_duplicate={result.skipped_duplicate}"
        )
        return {
            "read": result.read,
            "inserted": result.inserted,
            "skipped_duplicate": result.skipped_duplicate,
        }

    @task
    def upload_raw_snapshot(*, ds: str) -> dict:
        from retailflow.extract.raw_snapshot import bucket_from_env, client_from_env, upload_file

        path = ORDERS_DIR / f"orders_{ds}.csv"
        if not path.exists():
            raise FileNotFoundError(f"No orders file for logical date {ds}: {path}")

        result = upload_file(path, ds, client_from_env(), bucket_from_env())
        print(f"{path.name}: uploaded to s3://{result.bucket}/{result.key}")
        return {"key": result.key}

    @task
    def load_fx_rates(*, ds: str) -> dict:
        from datetime import date

        from retailflow.load.fx_rates import connection_from_env, load_date

        with connection_from_env() as conn:
            result = load_date(date.fromisoformat(ds), FX_CACHE_DIR, conn)

        print(
            f"{result.for_date}: inserted={result.inserted} "
            f"skipped_duplicate={result.skipped_duplicate}"
        )
        return {"inserted": result.inserted, "skipped_duplicate": result.skipped_duplicate}

    load_orders()
    upload_raw_snapshot()
    load_fx_rates()


retailflow_daily()
