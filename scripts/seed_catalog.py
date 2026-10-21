"""Seed source.products with the 20 SKUs referenced by generate_sample_orders.py's
CATALOG_SKUS. Deterministic (fixed seed) and idempotent (ON CONFLICT DO NOTHING).

Usage:
    python scripts/seed_catalog.py
"""

from __future__ import annotations

import os
import random
from decimal import Decimal

import psycopg

CATALOG_SKUS = [f"SKU-{i:04d}" for i in range(1, 21)]
CATEGORIES = ["Electronics", "Home", "Apparel", "Sports", "Books"]
SEED = 42

INSERT_SQL = """
    INSERT INTO source.products (product_id, product_name, category, unit_cost)
    VALUES (%(product_id)s, %(product_name)s, %(category)s, %(unit_cost)s)
    ON CONFLICT (product_id) DO NOTHING
"""


def connection_from_env() -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ.get("POSTGRES_USER", "retailflow"),
        password=os.environ.get("POSTGRES_PASSWORD", "retailflow"),
        dbname=os.environ.get("POSTGRES_DB", "retailflow"),
    )


def build_catalog() -> list[dict]:
    rng = random.Random(SEED)
    catalog = []
    for sku in CATALOG_SKUS:
        category = rng.choice(CATEGORIES)
        catalog.append(
            {
                "product_id": sku,
                "product_name": f"{category} Item {sku.split('-')[1]}",
                "category": category,
                "unit_cost": Decimal(rng.randint(500, 9999)) / 100,
            }
        )
    return catalog


def seed(conn: psycopg.Connection) -> tuple[int, int]:
    inserted = skipped = 0
    with conn.cursor() as cur:
        for product in build_catalog():
            cur.execute(INSERT_SQL, product)
            if cur.rowcount == 1:
                inserted += 1
            else:
                skipped += 1
    conn.commit()
    return inserted, skipped


def main() -> None:
    with connection_from_env() as conn:
        inserted, skipped = seed(conn)
    print(f"products: inserted={inserted} skipped_duplicate={skipped}")


if __name__ == "__main__":
    main()
