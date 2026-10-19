"""Idempotent loader: orders CSV (per docs/contracts/orders_csv.md) -> staging.orders."""

from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg

INSERT_SQL = """
    INSERT INTO staging.orders (
        order_id, order_line_id, order_timestamp, customer_country,
        product_id, quantity, unit_price, currency, order_status
    )
    VALUES (%(order_id)s, %(order_line_id)s, %(order_timestamp)s, %(customer_country)s,
            %(product_id)s, %(quantity)s, %(unit_price)s, %(currency)s, %(order_status)s)
    ON CONFLICT (order_line_id) DO NOTHING
"""


@dataclass
class LoadResult:
    path: Path
    read: int = 0
    inserted: int = 0
    skipped_duplicate: int = 0


def connection_from_env() -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ.get("POSTGRES_USER", "retailflow"),
        password=os.environ.get("POSTGRES_PASSWORD", "retailflow"),
        dbname=os.environ.get("POSTGRES_DB", "retailflow"),
    )


def load_file(path: Path, conn: psycopg.Connection) -> LoadResult:
    """Insert every row of one orders CSV, skipping order_line_ids already present.

    Idempotent by construction: ON CONFLICT (order_line_id) DO NOTHING makes a
    rerun of the same file, or a duplicate injected within the file, a no-op
    rather than an error or a double-counted row.
    """
    result = LoadResult(path=path)
    with path.open(newline="") as f, conn.cursor() as cur:
        for row in csv.DictReader(f):
            result.read += 1
            row = dict(row)
            row["quantity"] = int(row["quantity"]) if row["quantity"] != "" else None
            cur.execute(INSERT_SQL, row)
            if cur.rowcount == 1:
                result.inserted += 1
            else:
                result.skipped_duplicate += 1
    conn.commit()
    return result


def load_directory(directory: Path, conn: psycopg.Connection) -> list[LoadResult]:
    return [load_file(path, conn) for path in sorted(directory.glob("orders_*.csv"))]


def main() -> None:
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/samples/orders")
    with connection_from_env() as conn:
        results = load_directory(directory, conn)
    for r in results:
        print(
            f"{r.path.name}: read={r.read} "
            f"inserted={r.inserted} skipped_duplicate={r.skipped_duplicate}"
        )
    print(
        f"TOTAL: read={sum(r.read for r in results)} "
        f"inserted={sum(r.inserted for r in results)} "
        f"skipped_duplicate={sum(r.skipped_duplicate for r in results)}"
    )


if __name__ == "__main__":
    main()
