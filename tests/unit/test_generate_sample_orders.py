from datetime import date

from scripts.generate_sample_orders import COLUMNS, DEFECTS, generate_day


def test_deterministic_for_same_seed():
    first = generate_day(date(2026, 1, 1), rows_per_day=50, defect_rate=0.1, seed=42)
    second = generate_day(date(2026, 1, 1), rows_per_day=50, defect_rate=0.1, seed=42)
    assert first == second


def test_rows_have_contract_columns():
    rows = generate_day(date(2026, 1, 1), rows_per_day=20, defect_rate=0.0, seed=1)
    assert len(rows) == 20
    assert all(set(row.keys()) == set(COLUMNS) for row in rows)


def test_order_id_and_order_line_id_never_blank():
    rows = generate_day(date(2026, 1, 1), rows_per_day=200, defect_rate=0.3, seed=7)
    assert all(row["order_id"] and row["order_line_id"] for row in rows)


def test_high_defect_rate_produces_a_duplicate_order_line_id():
    rows = generate_day(date(2026, 1, 1), rows_per_day=300, defect_rate=0.5, seed=7)
    line_ids = [row["order_line_id"] for row in rows]
    assert len(set(line_ids)) < len(line_ids), "expected at least one injected duplicate"


def test_defect_list_is_not_empty():
    assert DEFECTS
