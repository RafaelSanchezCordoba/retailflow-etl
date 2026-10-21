"""Idempotent loader: Frankfurter FX rates (via extract.fx_rates) -> staging.fx_rates."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import psycopg

from retailflow.extract.fx_rates import fetch_rates

CURRENCIES = ["EUR", "USD", "GBP", "PLN", "SEK", "CHF"]

INSERT_SQL = """
    INSERT INTO staging.fx_rates (rate_date, currency, rate)
    VALUES (%(rate_date)s, %(currency)s, %(rate)s)
    ON CONFLICT (rate_date, currency) DO NOTHING
"""


@dataclass
class LoadResult:
    for_date: date
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


def load_date(for_date: date, cache_dir: Path, conn: psycopg.Connection) -> LoadResult:
    rates = fetch_rates(for_date, CURRENCIES, cache_dir)
    result = LoadResult(for_date=for_date)
    with conn.cursor() as cur:
        for currency, rate in rates.rates.items():
            cur.execute(INSERT_SQL, {"rate_date": for_date, "currency": currency, "rate": rate})
            if cur.rowcount == 1:
                result.inserted += 1
            else:
                result.skipped_duplicate += 1
    conn.commit()
    return result


def main() -> None:
    for_date = date.fromisoformat(sys.argv[1])
    cache_dir = Path("data/cache/fx_rates")
    with connection_from_env() as conn:
        result = load_date(for_date, cache_dir, conn)
    print(
        f"{result.for_date}: inserted={result.inserted} "
        f"skipped_duplicate={result.skipped_duplicate}"
    )


if __name__ == "__main__":
    main()
