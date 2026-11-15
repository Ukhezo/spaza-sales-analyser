"""The SQL queries must give the same answers as the pandas analysis."""

import pandas as pd
import pytest

from spaza_analyser import analysis
from spaza_analyser.data import prepare_sales
from spaza_analyser.database import build_database, list_queries, run_query
from spaza_analyser.sql_report import main as sql_main


@pytest.fixture
def sales():
    rows = [
        ("R1", "2025-01-26 07:10", "Bread", "Bakery", 2, 20.0, 16.0, "Cash"),
        ("R2", "2025-01-26 17:30", "Maize 5kg", "Groceries", 1, 75.0, 63.0, "Card"),
        ("R3", "2025-01-14 12:00", "Bread", "Bakery", 2, 20.0, 16.0, "Cash"),
        ("R4", "2025-02-02 08:00", "Airtime R10", "Airtime", 3, 10.0, 9.4, "Mobile wallet"),
        ("R5", "2025-02-15 18:45", "Maize 5kg", "Groceries", 2, 75.0, 63.0, "Cash"),
        ("R6", "2025-06-10 06:30", "Paraffin 1L", "Household", 4, 27.0, 22.0, "Cash"),
        ("R7", "2025-12-20 13:15", "Paraffin 1L", "Household", 1, 27.0, 22.0, "Card"),
    ]
    cols = ["receipt_id", "timestamp", "product", "category", "quantity", "unit_price", "unit_cost", "payment_method"]
    return prepare_sales(pd.DataFrame(rows, columns=cols))


@pytest.fixture
def conn(sales):
    connection = build_database(sales)
    yield connection
    connection.close()


def test_products_are_stored_once(conn):
    assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 7


def test_schema_rejects_bad_quantity(conn):
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO sales (receipt_id, sold_at, product_id, quantity, payment_method) "
            "VALUES ('X', '2025-01-01 10:00:00', 1, 0, 'Cash')"
        )


def test_headline_matches_pandas(sales, conn):
    sql = run_query(conn, "01_headline_numbers").iloc[0]
    s = analysis.summarise(sales)
    assert sql["revenue"] == pytest.approx(s.revenue)
    assert sql["gross_profit"] == pytest.approx(s.profit)
    assert sql["items_sold"] == s.items_sold
    assert sql["trading_days"] == s.trading_days


def test_monthly_matches_pandas(sales, conn):
    sql = run_query(conn, "02_monthly_sales").set_index("month")["revenue"]
    pandas = analysis.monthly_totals(sales)["revenue"]
    pandas.index = pandas.index.strftime("%Y-%m")
    pd.testing.assert_series_equal(sql, pandas.round(2), check_names=False)


def test_top_product_matches_pandas(sales, conn):
    assert run_query(conn, "03_top_products").iloc[0]["product"] == analysis.top_products(sales, 1).iloc[0]["product"]


def test_category_shares_add_up(conn):
    assert run_query(conn, "04_category_share")["share_pct"].sum() == pytest.approx(100, abs=0.2)


def test_payday_matches_pandas(sales, conn):
    sql = run_query(conn, "05_payday_effect").set_index("period")["avg_daily_revenue"]
    pandas = analysis.payday_effect(sales)["avg_daily_revenue"]
    for period in pandas.index:
        assert sql[period] == pytest.approx(pandas[period], abs=0.01)


def test_running_total_ends_at_total(sales, conn):
    ytd = run_query(conn, "08_running_total")["year_to_date"].iloc[-1]
    assert ytd == pytest.approx(sales["revenue"].sum())


def test_every_saved_query_runs(conn):
    assert len(list_queries()) == 10
    for path in list_queries():
        assert isinstance(run_query(conn, path.stem), pd.DataFrame)


def test_unknown_query_name(conn):
    with pytest.raises(ValueError, match="No query named"):
        run_query(conn, "does_not_exist")


def test_sql_report_cli(sales, tmp_path):
    csv = tmp_path / "sales.csv"
    sales.to_csv(csv, index=False)
    out = tmp_path / "sql_results.md"
    assert sql_main([str(csv), "--db", str(tmp_path / "shop.db"), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.count("```sql") == 10
    assert (tmp_path / "shop.db").exists()
