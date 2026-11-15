"""Business questions a shop owner cares about, answered with pandas."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass(frozen=True)
class Summary:
    revenue: float
    cost: float
    profit: float
    margin_pct: float
    sales_lines: int
    items_sold: int
    trading_days: int
    avg_daily_revenue: float
    first_day: pd.Timestamp
    last_day: pd.Timestamp


def summarise(df: pd.DataFrame) -> Summary:
    """Headline numbers for the whole period."""
    revenue = float(df["revenue"].sum())
    profit = float(df["profit"].sum())
    days = int(df["date"].nunique())
    return Summary(
        revenue=revenue,
        cost=float(df["cost"].sum()),
        profit=profit,
        margin_pct=(profit / revenue * 100) if revenue else 0.0,
        sales_lines=len(df),
        items_sold=int(df["quantity"].sum()),
        trading_days=days,
        avg_daily_revenue=revenue / days if days else 0.0,
        first_day=df["date"].min(),
        last_day=df["date"].max(),
    )


def monthly_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue, profit and margin for each month."""
    out = df.groupby("month")[["revenue", "cost", "profit"]].sum()
    out["margin_pct"] = out["profit"] / out["revenue"] * 100
    out["revenue_change_pct"] = out["revenue"].pct_change() * 100
    return out


def product_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Units, revenue, profit and margin per product, best earners first."""
    out = df.groupby(["product", "category"], as_index=False).agg(
        units=("quantity", "sum"), revenue=("revenue", "sum"), profit=("profit", "sum")
    )
    out["margin_pct"] = out["profit"] / out["revenue"] * 100
    out["profit_share_pct"] = out["profit"] / out["profit"].sum() * 100
    return out.sort_values("profit", ascending=False).reset_index(drop=True)


def top_products(df: pd.DataFrame, n: int = 10, by: str = "profit") -> pd.DataFrame:
    """The n best products ranked by 'profit', 'revenue' or 'units'."""
    if by not in {"profit", "revenue", "units"}:
        raise ValueError("by must be 'profit', 'revenue' or 'units'")
    return product_performance(df).sort_values(by, ascending=False).head(n).reset_index(drop=True)


def slow_movers(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Products earning the least profit: candidates to stock less or re-price."""
    return product_performance(df).tail(n).sort_values("profit").reset_index(drop=True)


def category_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue and profit by category, with each category's share."""
    out = df.groupby("category")[["revenue", "profit"]].sum()
    out["revenue_share_pct"] = out["revenue"] / out["revenue"].sum() * 100
    out["margin_pct"] = out["profit"] / out["revenue"] * 100
    return out.sort_values("revenue", ascending=False)


def weekday_pattern(df: pd.DataFrame) -> pd.DataFrame:
    """Average revenue for each day of the week."""
    daily = df.groupby(["date", "weekday"], as_index=False)["revenue"].sum()
    out = daily.groupby("weekday")["revenue"].mean().reindex(WEEKDAY_ORDER)
    return out.to_frame("avg_revenue")


def hourly_pattern(df: pd.DataFrame) -> pd.DataFrame:
    """Average revenue for each opening hour, to plan staff and restocking."""
    days = df["date"].nunique()
    out = df.groupby("hour")["revenue"].sum() / days
    return out.to_frame("avg_revenue")


def payday_effect(df: pd.DataFrame) -> pd.DataFrame:
    """Compare average daily revenue in the payday window (25th to 3rd) with the rest."""
    daily = df.groupby("date")["revenue"].sum().to_frame()
    day_of_month = daily.index.day
    daily["period"] = ["Payday (25th-3rd)" if (d >= 25 or d <= 3) else "Rest of month" for d in day_of_month]
    out = daily.groupby("period")["revenue"].agg(avg_daily_revenue="mean", days="count")
    return out


def payment_mix(df: pd.DataFrame) -> pd.DataFrame:
    """How customers pay, by number of sales and by value."""
    out = df.groupby("payment_method").agg(sales=("receipt_id", "count"), revenue=("revenue", "sum"))
    out["share_of_value_pct"] = out["revenue"] / out["revenue"].sum() * 100
    return out.sort_values("revenue", ascending=False)


def seasonal_products(df: pd.DataFrame, products: list[str]) -> pd.DataFrame:
    """Monthly units for selected products, e.g. paraffin vs cold drinks."""
    subset = df[df["product"].isin(products)]
    return subset.pivot_table(index="month", columns="product", values="quantity", aggfunc="sum", fill_value=0)


def insights(df: pd.DataFrame) -> list[str]:
    """Plain-language findings a shop owner can act on."""
    s = summarise(df)
    monthly = monthly_totals(df)
    best_month = monthly["revenue"].idxmax()
    worst_month = monthly["revenue"].idxmin()
    top = top_products(df, 1).iloc[0]
    cats = category_breakdown(df)
    weekdays = weekday_pattern(df)["avg_revenue"]
    hours = hourly_pattern(df)["avg_revenue"]
    payday = payday_effect(df)["avg_daily_revenue"]
    lift = (payday["Payday (25th-3rd)"] / payday["Rest of month"] - 1) * 100
    low_margin = cats["margin_pct"].idxmin()

    return [
        f"The shop made {rand(s.revenue)} in sales and {rand(s.profit)} gross profit "
        f"({s.margin_pct:.1f}% margin) over {s.trading_days} trading days.",
        f"Best month was {best_month.strftime('%B')} ({rand(monthly.loc[best_month, 'revenue'])}); "
        f"quietest was {worst_month.strftime('%B')} ({rand(monthly.loc[worst_month, 'revenue'])}).",
        f"{top['product']} is the biggest earner, bringing in {rand(top['profit'])} profit "
        f"({top['profit_share_pct']:.1f}% of the total).",
        f"Payday days (25th to 3rd) average {lift:.0f}% more sales than the rest of the month: "
        "stock up on bulk staples before the 25th.",
        f"{weekdays.idxmax()} is the busiest day and {weekdays.idxmin()} the quietest.",
        f"The busiest hour is {int(hours.idxmax()):02d}:00, so restock shelves before then.",
        f"{low_margin} has the thinnest margin ({cats.loc[low_margin, 'margin_pct']:.1f}%): "
        "it brings customers in but earns little on its own.",
    ]


def rand(value: float) -> str:
    """Format money the South African way: R 1 234 567.89."""
    sign = "-" if value < 0 else ""
    whole, cents = f"{abs(value):,.2f}".split(".")
    return f"{sign}R {whole.replace(',', ' ')}.{cents}"
