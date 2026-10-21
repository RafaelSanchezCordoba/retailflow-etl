import json
from datetime import date

import pytest

from retailflow.extract.fx_rates import FxRateUnavailable, fetch_rates


def test_fetch_rates_caches_to_disk(tmp_path, monkeypatch):
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(
                [{"date": "2026-01-02", "base": "EUR", "quote": "USD", "rate": 1.08}]
            )

    def fake_urlopen(url, timeout):
        calls.append(url)
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = fetch_rates(date(2026, 1, 2), ["USD"], tmp_path)
    assert result.rates == {"USD": 1.08}
    assert len(calls) == 1

    # second call for the same date reads the cache, no second HTTP call
    fetch_rates(date(2026, 1, 2), ["USD"], tmp_path)
    assert len(calls) == 1


def test_fetch_rates_raises_on_empty_response(tmp_path, monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps([])

    monkeypatch.setattr("urllib.request.urlopen", lambda url, timeout: FakeResponse())

    with pytest.raises(FxRateUnavailable):
        fetch_rates(date(1800, 1, 1), ["USD"], tmp_path)
