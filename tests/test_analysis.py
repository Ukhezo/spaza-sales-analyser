import pandas as pd
import pytest

from spaza_analyser import analysis
from spaza_analyser.cli import main
from spaza_analyser.data import SalesDataError, load_sales, prepare_sales


@pytest.fixture
def sales():
    """A tiny, hand-checkable set of sales."""
    rows = [
        # receipt, timestamp, product, category, qty, price, cost, payment
        ("R1", "2025-01-26 07:10", "Bread", "Bakery", 2, 20.0, 16.0, "Cash"),  # payday, Sunday
        ("R2", "2025-01-26 17:30", "Maize 5kg", "Groceries", 1, 75.0, 63.0, "Card"),
        ("R3", "2025-01-14 12:00", "Bread", "Bakery", 2, 20.0, 16.0, "Cash"),  # mid-month, Tuesday
        ("R4", "2025-02-02 08:00", "Airtime R10", "Airtime", 3, 10.0, 9.4, "Mobile wallet"),  # payday
        ("R5", "2025-02-15 18:45", "Maize 5kg", "Groceries", 2, 75.0, 63.0, "Cash"),
    ]
    cols = ["receipt_id", "timestamp", "product", "category", "quantity", "unit_price", "unit_cost", "payment_method"]
    return prepare_sales(pd.DataFrame(rows, columns=cols))


def test_money_columns(sales):
    first = sales.set_index("receipt_id").loc["R1"]
    assert first["revenue"] == 40.0
    assert first["cost"] == 32.0
    assert first["profit"] == 8.0


def test_summary_totals(sales):
    s = analysis.summarise(sales)
    assert s.revenue == pytest.approx(40 + 75 + 40 + 30 + 150)
    assert s.profit == pytest.approx(8 + 12 + 8 + 1.8 + 24)
    assert s.items_sold == 10
    assert s.trading_days == 4
    assert s.margin_pct == pytest.approx(53.8 / 335 * 100)


def test_monthly_totals(sales):
    monthly = analysis.monthly_totals(sales)
    assert monthly.loc[pd.Period("2025-01"), "revenue"] == pytest.approx(155)
    assert monthly.loc[pd.Period("2025-02"), "revenue"] == pytest.approx(180)
    assert monthly.loc[pd.Period("2025-02"), "revenue_change_pct"] == pytest.approx((180 / 155 - 1) * 100)


def test_top_products_by_profit_and_units(sales):
    assert analysis.top_products(sales, 1, by="profit").iloc[0]["product"] == "Maize 5kg"
    assert analysis.top_products(sales, 1, by="units").iloc[0]["product"] == "Bread"
    with pytest.raises(ValueError):
        analysis.top_products(sales, by="colour")


def test_slow_movers(sales):
    assert analysis.slow_movers(sales, 1).iloc[0]["product"] == "Airtime R10"


def test_payday_effect(sales):
    payday = analysis.payday_effect(sales)
    # payday days: 26 Jan (R115) and 2 Feb (R30); other days: 14 Jan (R40) and 15 Feb (R150)
    assert payday.loc["Payday (25th-3rd)", "avg_daily_revenue"] == pytest.approx(72.5)
    assert payday.loc["Rest of month", "avg_daily_revenue"] == pytest.approx(95)


def test_weekday_order(sales):
    days = analysis.weekday_pattern(sales)
    assert list(days.index) == analysis.WEEKDAY_ORDER
    # 26 Jan (R115) and 2 Feb (R30) 2025 are both Sundays
    assert days.loc["Sunday", "avg_revenue"] == pytest.approx(72.5)


def test_payment_mix_shares_add_up(sales):
    mix = analysis.payment_mix(sales)
    assert mix["share_of_value_pct"].sum() == pytest.approx(100)


def test_insights_are_plain_sentences(sales):
    lines = analysis.insights(sales)
    assert len(lines) == 7
    assert all(isinstance(line, str) and line for line in lines)


@pytest.mark.parametrize(
    "value, expected",
    [(0, "R 0.00"), (1234567.891, "R 1 234 567.89"), (-50, "-R 50.00"), (999.995, "R 1 000.00")],
)
def test_rand_format(value, expected):
    assert analysis.rand(value) == expected


def test_missing_columns_are_reported():
    with pytest.raises(SalesDataError, match="Missing columns"):
        prepare_sales(pd.DataFrame({"product": ["Bread"]}))


def test_bad_numbers_are_reported(sales):
    raw = sales[
        ["receipt_id", "timestamp", "product", "category", "quantity", "unit_price", "unit_cost", "payment_method"]
    ].copy()
    raw["quantity"] = raw["quantity"].astype(object)
    raw.loc[0, "quantity"] = "two"
    with pytest.raises(SalesDataError, match="invalid"):
        prepare_sales(raw)


def test_negative_quantity_rejected(sales):
    raw = sales.copy()
    raw.loc[0, "quantity"] = -1
    with pytest.raises(SalesDataError, match="greater than zero"):
        prepare_sales(raw)


def test_load_missing_file(tmp_path):
    with pytest.raises(SalesDataError, match="not found"):
        load_sales(tmp_path / "nope.csv")


def test_cli_writes_report_and_charts(sales, tmp_path, capsys):
    csv = tmp_path / "sales.csv"
    sales.to_csv(csv, index=False)
    out = tmp_path / "out"
    assert main([str(csv), "--out", str(out), "--shop", "Test Spaza"]) == 0
    report = (out / "report.md").read_text(encoding="utf-8")
    assert report.startswith("# Test Spaza: sales report")
    assert len(list((out / "charts").glob("*.png"))) == 7
    assert "Gross profit" in capsys.readouterr().out


def test_cli_bad_file_returns_error(tmp_path, capsys):
    assert main([str(tmp_path / "missing.csv")]) == 1
    assert "Error" in capsys.readouterr().err
