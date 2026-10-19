"""Generate deterministic sample orders CSV files per the contract in
docs/contracts/orders_csv.md.

Usage:
    python scripts/generate_sample_orders.py --start-date 2026-01-01 --end-date 2026-01-03
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

COUNTRIES = ["DE", "FR", "ES", "IT", "NL", "PL", "SE", "PT", "BE", "AT"]
CURRENCIES = ["EUR", "USD", "GBP", "PLN", "SEK", "CHF"]
CATALOG_SKUS = [f"SKU-{i:04d}" for i in range(1, 21)]
STATUSES = ["completed", "completed", "completed", "completed", "cancelled", "refunded"]

DEFECTS = [
    "duplicate_order_line_id",
    "null_customer_country",
    "missing_product_id",
    "non_positive_quantity",
    "invalid_unit_price",
    "invalid_currency",
    "invalid_order_status",
    "invalid_timestamp",
]

COLUMNS = [
    "order_id",
    "order_line_id",
    "order_timestamp",
    "customer_country",
    "product_id",
    "quantity",
    "unit_price",
    "currency",
    "order_status",
]


def _make_row(rng: random.Random, logical_date: date, order_seq: int, line_no: int) -> dict:
    order_id = f"ORD-{logical_date:%Y%m%d}-{order_seq:06d}"
    hour = rng.randint(0, 23)
    minute = rng.randint(0, 59)
    timestamp = datetime(
        logical_date.year, logical_date.month, logical_date.day, hour, minute, tzinfo=UTC
    )
    return {
        "order_id": order_id,
        "order_line_id": f"{order_id}-L{line_no}",
        "order_timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "customer_country": rng.choice(COUNTRIES),
        "product_id": rng.choice(CATALOG_SKUS),
        "quantity": rng.randint(1, 5),
        "unit_price": str(Decimal(rng.randint(500, 29999)) / 100),
        "currency": rng.choice(CURRENCIES),
        "order_status": rng.choice(STATUSES),
    }


def _apply_defect(row: dict, defect: str, previous_rows: list[dict], rng: random.Random) -> dict:
    row = dict(row)
    if defect == "duplicate_order_line_id" and previous_rows:
        return dict(rng.choice(previous_rows))
    if defect == "null_customer_country":
        row["customer_country"] = ""
    elif defect == "missing_product_id":
        row["product_id"] = "SKU-9999"
    elif defect == "non_positive_quantity":
        row["quantity"] = rng.choice([0, -1, -3])
    elif defect == "invalid_unit_price":
        row["unit_price"] = rng.choice(["", "-5.00", "0"])
    elif defect == "invalid_currency":
        row["currency"] = "XXX"
    elif defect == "invalid_order_status":
        row["order_status"] = "pending_review"
    elif defect == "invalid_timestamp":
        row["order_timestamp"] = "not-a-timestamp"
    return row


def generate_day(
    logical_date: date, rows_per_day: int, defect_rate: float, seed: int
) -> list[dict]:
    rng = random.Random(f"{seed}:{logical_date.isoformat()}")
    rows: list[dict] = []
    order_seq = 1
    line_no = 1
    while len(rows) < rows_per_day:
        lines_in_order = rng.randint(1, 3)
        for _ in range(lines_in_order):
            if len(rows) >= rows_per_day:
                break
            row = _make_row(rng, logical_date, order_seq, line_no)
            if rng.random() < defect_rate:
                row = _apply_defect(row, rng.choice(DEFECTS), rows, rng)
            rows.append(row)
            line_no += 1
        order_seq += 1
        line_no = 1
    return rows


def write_day(output_dir: Path, logical_date: date, rows: list[dict]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"orders_{logical_date:%Y-%m-%d}.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/samples/orders"))
    parser.add_argument("--rows-per-day", type=int, default=60)
    parser.add_argument("--defect-rate", type=float, default=0.08)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    for logical_date in daterange(args.start_date, args.end_date):
        rows = generate_day(logical_date, args.rows_per_day, args.defect_rate, args.seed)
        path = write_day(args.output_dir, logical_date, rows)
        print(f"wrote {len(rows)} rows -> {path}")


if __name__ == "__main__":
    main()
