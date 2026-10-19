import psycopg
import pytest

from retailflow.load.orders import connection_from_env, load_file

CSV_HEADER = (
    "order_id,order_line_id,order_timestamp,customer_country,product_id,"
    "quantity,unit_price,currency,order_status\n"
)
# Prefixed order_id so fixture cleanup only ever touches this test's own rows --
# staging.orders is the real shared dev table, not a disposable test schema.
TEST_ORDER_ID = "ORD-TEST-1"
ROW = f"{TEST_ORDER_ID},{TEST_ORDER_ID}-L1,2026-01-01T00:00:00Z,DE,SKU-0001,2,19.99,EUR,completed\n"


def _delete_test_rows(connection: psycopg.Connection) -> None:
    with connection.cursor() as cur:
        cur.execute("DELETE FROM staging.orders WHERE order_id = %s", (TEST_ORDER_ID,))
    connection.commit()


@pytest.fixture
def conn():
    try:
        connection = connection_from_env()
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable; start it with `docker compose up -d`")
    _delete_test_rows(connection)
    yield connection
    _delete_test_rows(connection)
    connection.close()


def test_load_is_idempotent_within_and_across_runs(conn, tmp_path):
    path = tmp_path / "orders_2026-01-01.csv"
    path.write_text(CSV_HEADER + ROW + ROW)  # duplicate order_line_id within the file

    first = load_file(path, conn)
    assert (first.read, first.inserted, first.skipped_duplicate) == (2, 1, 1)

    second = load_file(path, conn)
    assert (second.read, second.inserted, second.skipped_duplicate) == (2, 0, 2)

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM staging.orders WHERE order_id = %s", (TEST_ORDER_ID,))
        assert cur.fetchone()[0] == 1
