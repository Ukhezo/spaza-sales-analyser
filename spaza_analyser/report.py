"""Write a Markdown sales report with tables, charts and recommendations."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import analysis, charts
from .analysis import rand


def _table(df: pd.DataFrame, money: list[str] = (), pct: list[str] = (), ints: list[str] = ()) -> str:
    shown = df.copy()
    for col in money:
        shown[col] = shown[col].map(rand)
    for col in pct:
        shown[col] = shown[col].map(lambda v: "" if pd.isna(v) else f"{v:.1f}%")
    for col in ints:
        shown[col] = shown[col].map(lambda v: f"{int(v):,}".replace(",", " "))
    return shown.to_markdown(index=False)


def build_report(df: pd.DataFrame, out_dir: str | Path, shop_name: str = "Spaza shop", top_n: int = 10) -> Path:
    """Create report.md and its charts in out_dir. Returns the report path."""
    out_dir = Path(out_dir)
    chart_dir = out_dir / "charts"
    paths = charts.make_all_charts(df, chart_dir)
    rel = {k: p.relative_to(out_dir).as_posix() for k, p in paths.items()}

    s = analysis.summarise(df)
    monthly = analysis.monthly_totals(df).reset_index()
    monthly["month"] = monthly["month"].map(lambda p: p.strftime("%b %Y"))
    top = analysis.top_products(df, top_n)
    slow = analysis.slow_movers(df, 5)
    cats = analysis.category_breakdown(df).reset_index()
    pay = analysis.payment_mix(df).reset_index()

    lines = [
        f"# {shop_name}: sales report",
        "",
        f"Period: **{s.first_day:%d %b %Y} to {s.last_day:%d %b %Y}**",
        "",
        "## Headline numbers",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Sales | {rand(s.revenue)} |",
        f"| Gross profit | {rand(s.profit)} |",
        f"| Gross margin | {s.margin_pct:.1f}% |",
        f"| Items sold | {s.items_sold:,} |".replace(",", " "),
        f"| Trading days | {s.trading_days} |",
        f"| Average sales per day | {rand(s.avg_daily_revenue)} |",
        "",
        "## Key findings",
        "",
        *[f"- {line}" for line in analysis.insights(df)],
        "",
        "## Monthly trend",
        "",
        f"![Monthly sales and profit]({rel['monthly']})",
        "",
        _table(
            monthly[["month", "revenue", "profit", "margin_pct", "revenue_change_pct"]].rename(
                columns={"revenue_change_pct": "change_pct"}
            ),
            money=["revenue", "profit"],
            pct=["margin_pct", "change_pct"],
        ),
        "",
        "## Best products",
        "",
        f"![Top products]({rel['top_products']})",
        "",
        _table(
            top[["product", "category", "units", "revenue", "profit", "margin_pct"]],
            money=["revenue", "profit"],
            pct=["margin_pct"],
            ints=["units"],
        ),
        "",
        "## Slow movers",
        "",
        "These earn the least profit. Consider stocking less, re-pricing or bundling them.",
        "",
        _table(
            slow[["product", "units", "revenue", "profit", "margin_pct"]],
            money=["revenue", "profit"],
            pct=["margin_pct"],
            ints=["units"],
        ),
        "",
        "## Categories",
        "",
        f"![Sales by category]({rel['categories']})",
        "",
        _table(cats, money=["revenue", "profit"], pct=["revenue_share_pct", "margin_pct"]),
        "",
        "## When customers shop",
        "",
        f"![Sales by weekday]({rel['weekdays']})",
        "",
        f"![Sales by hour]({rel['hours']})",
        "",
        f"![Payday effect]({rel['payday']})",
        "",
        "## Seasonal stock",
        "",
        f"![Paraffin vs cold drinks]({rel['seasonal']})",
        "",
        "## How customers pay",
        "",
        f"![Payment methods]({rel['payments']})",
        "",
        _table(pay, money=["revenue"], pct=["share_of_value_pct"], ints=["sales"]),
        "",
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
