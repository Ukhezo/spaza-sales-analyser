"""Load sales into a SQLite database and run the SQL queries in sql/queries/."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
QUERY_DIR = SQL_DIR / "queries"


def build_database(df: pd.DataFrame, db_path: str | Path = ":memory:") -> sqlite3.Connection:
    """Create the products and sales tables from a prepared sales DataFrame.

    Products are stored once (normalised), and each sale line points to its product.
    Returns an open connection to the database.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))

    products = (
        df[["product", "category", "unit_price", "unit_cost"]]
        .drop_duplicates("product")
        .sort_values("product")
        .reset_index(drop=True)
    )
    products.insert(0, "product_id", range(1, len(products) + 1))
    conn.executemany(
        "INSERT INTO products (product_id, name, category, unit_price, unit_cost) VALUES (?, ?, ?, ?, ?)",
        products.itertuples(index=False, name=None),
    )

    ids = dict(zip(products["product"], products["product_id"], strict=True))
    rows = zip(
        df["receipt_id"],
        df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        df["product"].map(ids),
        df["quantity"].astype(int),
        df["payment_method"],
        strict=True,
    )
    conn.executemany(
        "INSERT INTO sales (receipt_id, sold_at, product_id, quantity, payment_method) VALUES (?, ?, ?, ?, ?)",
        ((r, t, int(p), int(q), m) for r, t, p, q, m in rows),
    )
    conn.commit()
    return conn


def list_queries() -> list[Path]:
    """All saved SQL queries, in order."""
    return sorted(QUERY_DIR.glob("*.sql"))


def query_title(path: Path) -> str:
    """The first comment line of a query file, used as its title."""
    first = path.read_text(encoding="utf-8").splitlines()[0]
    return first.lstrip("- ").strip()


def run_query(conn: sqlite3.Connection, name: str) -> pd.DataFrame:
    """Run a saved query by file name (with or without .sql) and return the result."""
    matches = [p for p in list_queries() if p.stem == name.removesuffix(".sql")]
    if not matches:
        raise ValueError(f"No query named {name!r}. Available: {', '.join(p.stem for p in list_queries())}")
    return pd.read_sql_query(matches[0].read_text(encoding="utf-8"), conn)


def run_all(conn: sqlite3.Connection) -> list[tuple[Path, pd.DataFrame]]:
    return [(path, pd.read_sql_query(path.read_text(encoding="utf-8"), conn)) for path in list_queries()]
