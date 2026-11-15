"""Build the SQLite database and write every SQL query with its result to a Markdown file.

Usage:
    python -m spaza_analyser.sql_report data/sales_2025.csv --db data/spaza.db --out reports/sql_results.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .data import SalesDataError, load_sales
from .database import build_database, query_title, run_all


def write_sql_report(results, out_path: Path) -> Path:
    lines = [
        "# SQL analysis results",
        "",
        "Each query lives in [`sql/queries/`](../sql/queries) and runs against the SQLite database built by "
        "`spaza_analyser.sql_report`. Tables: `products` (one row per item) and `sales` (one row per sale line).",
        "",
    ]
    for path, df in results:
        sql = path.read_text(encoding="utf-8").strip()
        lines += [
            f"## {query_title(path)}",
            "",
            f"[`{path.name}`](../sql/queries/{path.name})",
            "",
            "```sql",
            sql,
            "```",
            "",
            df.to_markdown(index=False, floatfmt=",.2f"),
            "",
        ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spaza_analyser.sql_report", description=__doc__.splitlines()[0])
    parser.add_argument("csv", help="path to the sales CSV file")
    parser.add_argument("--db", default="data/spaza.db", help="SQLite file to create (default: data/spaza.db)")
    parser.add_argument("--out", default="reports/sql_results.md", help="Markdown file for the results")
    args = parser.parse_args(argv)

    try:
        df = load_sales(args.csv)
    except SalesDataError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = build_database(df, db_path)
    try:
        products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        sales = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
        print(f"Database {db_path}: {products} products, {sales:,} sales".replace(",", " "))
        results = run_all(conn)
    finally:
        conn.close()

    for path, df_result in results:
        print(f"\n{query_title(path)}\n{df_result.head(5).to_string(index=False)}")
    out = write_sql_report(results, Path(args.out))
    print(f"\nSQL results written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
