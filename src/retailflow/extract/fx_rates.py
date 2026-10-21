"""Fetch EUR exchange rates from the Frankfurter API (https://frankfurter.dev/),
caching the raw JSON payload per date for reproducibility and offline tests.

Frankfurter's v2 already returns the last available rate for a date with no
published rate of its own (e.g. a request for tomorrow, before today's close,
returns today's rate under today's date) -- confirmed against the live API,
not assumed. An empty response only happens for dates outside its coverage
(pre-1999, or far future); that is treated as a hard failure, not synthesized.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

API_URL = "https://api.frankfurter.dev/v2/rates"


class FxRateUnavailable(Exception):
    pass


@dataclass
class FxRates:
    for_date: date
    rates: dict[str, float]  # currency -> units per 1 EUR


def _cache_path(cache_dir: Path, for_date: date, symbols: list[str]) -> Path:
    # Symbols are part of the key -- a cache file for a narrower symbol set
    # must never be served back as if it covered a wider one.
    return cache_dir / f"{for_date.isoformat()}_{'-'.join(sorted(symbols))}.json"


def fetch_rates(for_date: date, symbols: list[str], cache_dir: Path) -> FxRates:
    """Rates for every symbol, base EUR, for one date. Reads/writes a disk cache
    so a rerun for the same (date, symbols) never re-hits the live API."""
    path = _cache_path(cache_dir, for_date, symbols)
    if path.exists():
        payload = json.loads(path.read_text())
    else:
        url = f"{API_URL}?date={for_date.isoformat()}&base=EUR&quotes={','.join(symbols)}"
        request = urllib.request.Request(url, headers={"User-Agent": "retailflow-etl"})
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read())
        cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))

    if not payload:
        raise FxRateUnavailable(f"no rate available for {for_date.isoformat()}")
    return FxRates(for_date=for_date, rates={row["quote"]: row["rate"] for row in payload})


def main() -> None:
    import sys

    for_date = date.fromisoformat(sys.argv[1])
    symbols = sys.argv[2].split(",") if len(sys.argv) > 2 else ["USD", "GBP", "PLN", "SEK", "CHF"]
    result = fetch_rates(for_date, symbols, Path("data/cache/fx_rates"))
    print(f"{result.for_date}: {result.rates}")


if __name__ == "__main__":
    main()
