"""Command-line entry point: python -m spaza_analyser data/sales_2025.csv"""

from __future__ import annotations

import argparse
import sys

from . import analysis
from .data import SalesDataError, load_sales
from .report import build_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spaza_analyser",
        description="Analyse spaza shop sales and write a report with charts.",
    )
    parser.add_argument("csv", help="path to the sales CSV file")
    parser.add_argument("--out", default="reports", help="folder for report.md and charts (default: reports)")
    parser.add_argument("--shop", default="Spaza shop", help="shop name for the report title")
    parser.add_argument("--top", type=int, default=10, help="how many top products to list (default: 10)")
    args = parser.parse_args(argv)

    try:
        df = load_sales(args.csv)
    except SalesDataError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    s = analysis.summarise(df)
    print(f"{args.shop}: {s.first_day:%d %b %Y} to {s.last_day:%d %b %Y}")
    print(f"  Sales        {analysis.rand(s.revenue)}")
    print(f"  Gross profit {analysis.rand(s.profit)} ({s.margin_pct:.1f}% margin)")
    print()
    for line in analysis.insights(df):
        print(f"  * {line}")

    path = build_report(df, args.out, shop_name=args.shop, top_n=args.top)
    print(f"\nReport written to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
