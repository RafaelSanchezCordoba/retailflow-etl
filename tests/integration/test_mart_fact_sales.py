"""Proves mart.v_orders_validated's hard/soft-invalid split (sql/marts/002,
003) against a known, isolated set of staging.orders rows -- one per
reject_reason, plus the soft-invalid (missing product) and valid cases.
"""

from datetime import date

import psycopg
import pytest

from retailflow.load.orders import connection_from_env

TEST_DATE = date(1902, 1, 1)
TEST_ORDER_ID = "ORD-TEST-MART"
TEST_PRODUCT_ID = "TEST-PRODUCT-MART"
TS = f"{TEST_DATE.isoformat()}T00:00:00Z"

ORDER_COLUMNS = (
    "order_id, order_line_id, order_timestamp, customer_country, "
    "product_id, quantity, unit_price, currency, order_status"
)

# (line suffix, order_timestamp, customer_country, product_id, quantity,
#  unit_price, currency, order_status) -> expected reject_reason, or None if valid.
ROWS = [
    ("valid-completed", TS, "DE", TEST_PRODUCT_ID, 2, "10.00", "EUR", "completed", None),
    ("valid-cancelled", TS, "DE", TEST_PRODUCT_ID, 1, "10.00", "EUR", "cancelled", None),
    ("soft-missing-product", TS, "DE", "NO-SUCH-SKU", 1, "5.00", "EUR", "completed", None),
    ("null-country", TS, "", TEST_PRODUCT_ID, 1, "10.00", "EUR", "completed", "null_country"),
    ("bad-quantity", TS, "DE", TEST_PRODUCT_ID, 0, "10.00", "EUR", "completed",
        "invalid_quantity"),
    ("bad-price", TS, "DE", TEST_PRODUCT_ID, 1, "not-a-price", "EUR", "completed",
        "invalid_unit_price"),
    ("bad-timestamp", "not-a-timestamp", "DE", TEST_PRODUCT_ID, 1, "10.00", "EUR", "completed",
        "invalid_timestamp"),
    ("bad-status", TS, "DE", TEST_PRODUCT_ID, 1, "10.00", "EUR", "pending",
        "invalid_order_status"),
    ("bad-currency", TS, "DE", TEST_PRODUCT_ID, 1, "10.00", "ZZZ", "completed",
        "unresolvable_currency"),
]


def _line_id(suffix: str) -> str:
    return f"{TEST_ORDER_ID}-{suffix}"


def _cleanup(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM staging.orders WHERE order_id = %s", (TEST_ORDER_ID,))
        cur.execute("DELETE FROM source.products WHERE product_id = %s", (TEST_PRODUCT_ID,))
        cur.execute("DELETE FROM staging.fx_rates WHERE rate_date = %s", (TEST_DATE,))
    conn.commit()


@pytest.fixture
def conn():
    try:
        connection = connection_from_env()
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable; start it with `docker compose up -d`")
    _cleanup(connection)
    with connection.cursor() as cur:
        cur.execute(
            "INSERT INTO source.products (product_id, product_name, category, unit_cost) "
            "VALUES (%s, 'Test Product', 'Test', 4.00)",
            (TEST_PRODUCT_ID,),
        )
        cur.execute(
            "INSERT INTO staging.fx_rates (rate_date, currency, rate) VALUES (%s, 'EUR', 1.0)",
            (TEST_DATE,),
        )
        for suffix, ts, country, product_id, qty, price, currency, status, _ in ROWS:
            cur.execute(
                f"INSERT INTO staging.orders ({ORDER_COLUMNS}) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    TEST_ORDER_ID,
                    _line_id(suffix),
                    ts,
                    country,
                    product_id,
                    qty,
                    price,
                    currency,
                    status,
                ),
            )
    connection.commit()
    yield connection
    _cleanup(connection)
    connection.close()


def test_reject_reasons_match_expected(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT order_line_id, reject_reason FROM mart.v_orders_validated "
            "WHERE order_id = %s",
            (TEST_ORDER_ID,),
        )
        actual = dict(cur.fetchall())

    expected = {_line_id(suffix): reason for suffix, *_, reason in ROWS}
    assert actual == expected


def test_fact_sales_keeps_valid_and_soft_invalid_rows(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT order_line_id, net_amount_eur, margin_eur FROM mart.fact_sales "
            "WHERE order_id = %s ORDER BY order_line_id",
            (TEST_ORDER_ID,),
        )
        rows = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

    assert rows[_line_id("valid-completed")] == (20.00, 12.00)
    assert rows[_line_id("valid-cancelled")] == (0.00, None)
    assert rows[_line_id("soft-missing-product")] == (5.00, None)
    assert set(rows) == {
        _line_id("valid-completed"),
        _line_id("valid-cancelled"),
        _line_id("soft-missing-product"),
    }


def test_fact_sales_rejects_excludes_valid_rows(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT order_line_id FROM mart.fact_sales_rejects WHERE order_id = %s",
            (TEST_ORDER_ID,),
        )
        rejected = {r[0] for r in cur.fetchall()}

    expected_rejects = {
        _line_id(suffix) for suffix, *_, reason in ROWS if reason is not None
    }
    assert rejected == expected_rejects
