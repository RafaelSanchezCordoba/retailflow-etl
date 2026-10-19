import psycopg
import pytest

from retailflow.load.orders import connection_from_env, load_file

CSV_HEADER = (
    "order_id,order_line_id,order_timestamp,customer_country,product_id,"
    "quantity,unit_price,currency,order_status\n"
)
ROW = "ORD-1,ORD-1-L1,2026-01-01T00:00:00Z,DE,SKU-0001,2,19.99,EUR,completed\n"


@pytest.fixture
def conn():
    try:
        connection = connection_from_env()
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable; start it with `docker compose up -d`")
    with connection.cursor() as cur:
        cur.execute("DELETE FROM staging.orders")
    connection.commit()
    yield connection
    connection.close()


def test_load_is_idempotent_within_and_across_runs(conn, tmp_path):
    path = tmp_path / "orders_2026-01-01.csv"
    path.write_text(CSV_HEADER + ROW + ROW)  # duplicate order_line_id within the file

    first = load_file(path, conn)
    assert (first.read, first.inserted, first.skipped_duplicate) == (2, 1, 1)

    second = load_file(path, conn)
    assert (second.read, second.inserted, second.skipped_duplicate) == (2, 0, 2)

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM staging.orders")
        assert cur.fetchone()[0] == 1
