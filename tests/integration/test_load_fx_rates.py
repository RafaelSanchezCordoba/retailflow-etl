from datetime import date

import psycopg
import pytest

from retailflow.extract.fx_rates import FxRates
from retailflow.load.fx_rates import connection_from_env, load_date

# Fixed far-past date so this test's rows never collide with real pipeline data.
TEST_DATE = date(1901, 1, 1)


def _delete_test_rows(connection: psycopg.Connection) -> None:
    with connection.cursor() as cur:
        cur.execute("DELETE FROM staging.fx_rates WHERE rate_date = %s", (TEST_DATE,))
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


def test_load_is_idempotent(conn, tmp_path, monkeypatch):
    fake_rates = FxRates(for_date=TEST_DATE, rates={"USD": 1.1, "GBP": 0.9})
    monkeypatch.setattr(
        "retailflow.load.fx_rates.fetch_rates", lambda for_date, symbols, cache_dir: fake_rates
    )

    first = load_date(TEST_DATE, tmp_path, conn)
    assert (first.inserted, first.skipped_duplicate) == (2, 0)

    second = load_date(TEST_DATE, tmp_path, conn)
    assert (second.inserted, second.skipped_duplicate) == (0, 2)

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM staging.fx_rates WHERE rate_date = %s", (TEST_DATE,))
        assert cur.fetchone()[0] == 2
