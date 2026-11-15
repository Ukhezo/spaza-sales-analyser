"""Charts saved as PNG files, in one consistent style."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to files, no window needed
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from . import analysis  # noqa: E402

GREEN = "#1f7a4d"
GOLD = "#e0a526"
INK = "#1d2420"
MUTED = "#8a948e"
PALETTE = ["#1f7a4d", "#e0a526", "#2f6fb0", "#c4533a", "#7b5ea7", "#4f9d9a", "#a08a6a"]


def _rand_axis(value, _pos):
    if abs(value) >= 1_000_000:
        return f"R{value / 1_000_000:.1f}m"
    if abs(value) >= 1_000:
        return f"R{value / 1_000:.0f}k"
    return f"R{value:.0f}"


def _style(ax, title: str, subtitle: str | None = None):
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", color=INK, pad=22 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=10, color=MUTED)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#d5dad6")
    ax.spines["bottom"].set_color("#d5dad6")
    ax.tick_params(colors="#4b544f", labelsize=9)
    ax.grid(axis="y", color="#eceeec", linewidth=0.8)
    ax.set_axisbelow(True)


def _save(fig, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
    return path


def monthly_revenue_chart(df: pd.DataFrame, out_dir: Path) -> Path:
    monthly = analysis.monthly_totals(df)
    labels = [p.strftime("%b") for p in monthly.index]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(labels, monthly["revenue"], color=GREEN, width=0.65, label="Sales")
    ax.bar(labels, monthly["profit"], color=GOLD, width=0.65, label="Gross profit")
    ax.yaxis.set_major_formatter(FuncFormatter(_rand_axis))
    _style(ax, "Monthly sales and gross profit", "December holiday peak, quieter January")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    return _save(fig, out_dir, "monthly_revenue.png")


def top_products_chart(df: pd.DataFrame, out_dir: Path, n: int = 10) -> Path:
    top = analysis.top_products(df, n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    bars = ax.barh(top["product"], top["profit"], color=GREEN, height=0.62)
    for bar, value in zip(bars, top["profit"], strict=True):
        ax.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            "  " + _rand_axis(value, None),
            va="center",
            fontsize=9,
            color=INK,
        )
    ax.xaxis.set_major_formatter(FuncFormatter(_rand_axis))
    _style(ax, f"Top {n} products by gross profit", "Which lines actually pay the bills")
    ax.grid(axis="x", color="#eceeec", linewidth=0.8)
    ax.grid(axis="y", visible=False)
    return _save(fig, out_dir, "top_products.png")


def category_chart(df: pd.DataFrame, out_dir: Path) -> Path:
    cats = analysis.category_breakdown(df)
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    wedges, _texts, autotexts = ax.pie(
        cats["revenue"],
        labels=None,
        colors=PALETTE[: len(cats)],
        startangle=90,
        counterclock=False,
        autopct=lambda pct: f"{pct:.0f}%" if pct >= 4 else "",
        pctdistance=0.78,
        wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2},
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontsize(9)
        t.set_fontweight("bold")
    ax.legend(wedges, cats.index, frameon=False, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=9)
    ax.set_title("Share of sales by category", loc="left", fontsize=14, fontweight="bold", color=INK)
    return _save(fig, out_dir, "categories.png")


def weekday_chart(df: pd.DataFrame, out_dir: Path) -> Path:
    days = analysis.weekday_pattern(df)["avg_revenue"]
    colors = [GOLD if d in ("Friday", "Saturday", "Sunday") else GREEN for d in days.index]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.bar([d[:3] for d in days.index], days.values, color=colors, width=0.6)
    ax.yaxis.set_major_formatter(FuncFormatter(_rand_axis))
    _style(ax, "Average sales by day of the week", "Weekends (gold) are the busiest")
    return _save(fig, out_dir, "weekdays.png")


def hourly_chart(df: pd.DataFrame, out_dir: Path) -> Path:
    hours = analysis.hourly_pattern(df)["avg_revenue"]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.plot(hours.index, hours.values, color=GREEN, linewidth=2.5, marker="o", markersize=5)
    ax.fill_between(hours.index, hours.values, color=GREEN, alpha=0.08)
    ax.set_xticks(hours.index)
    ax.set_xticklabels([f"{h:02d}:00" for h in hours.index], rotation=45)
    ax.yaxis.set_major_formatter(FuncFormatter(_rand_axis))
    _style(ax, "Average sales by hour", "Morning and after-work rushes")
    return _save(fig, out_dir, "hours.png")


def payday_chart(df: pd.DataFrame, out_dir: Path) -> Path:
    # average each day-of-month only over the months that actually have that day
    per_date = df.groupby("date")["revenue"].sum()
    daily = per_date.groupby(per_date.index.day).mean()
    colors = [GOLD if (d >= 25 or d <= 3) else GREEN for d in daily.index]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.bar(daily.index, daily.values, color=colors, width=0.75)
    ax.set_xticks(range(1, 32, 2))
    ax.set_xlabel("Day of the month", color="#4b544f", fontsize=9)
    ax.yaxis.set_major_formatter(FuncFormatter(_rand_axis))
    _style(ax, "Average sales by day of the month", "Payday window (25th to 3rd) in gold")
    return _save(fig, out_dir, "payday.png")


def seasonal_chart(df: pd.DataFrame, out_dir: Path) -> Path:
    styles = {"Paraffin 1L": GOLD, "Cold drink 2L": "#2f6fb0"}
    data = analysis.seasonal_products(df, list(styles))
    fig, ax = plt.subplots(figsize=(10, 4.4))
    if data.empty:
        ax.text(
            0.5,
            0.5,
            "No paraffin or cold drink sales in this data",
            ha="center",
            va="center",
            transform=ax.transAxes,
            color=MUTED,
        )
    labels = [p.strftime("%b") for p in data.index]
    for product, color in styles.items():
        if product in data.columns:
            ax.plot(labels, data[product], color=color, linewidth=2.5, marker="o", label=product)
    ax.set_ylabel("Units sold", color="#4b544f", fontsize=9)
    _style(ax, "Seasonal stock: paraffin vs cold drinks", "Paraffin peaks in winter, cold drinks in summer")
    if not data.empty:
        ax.legend(frameon=False, fontsize=9)
    return _save(fig, out_dir, "seasonal.png")


def make_all_charts(df: pd.DataFrame, out_dir: str | Path) -> dict[str, Path]:
    out_dir = Path(out_dir)
    return {
        "monthly": monthly_revenue_chart(df, out_dir),
        "top_products": top_products_chart(df, out_dir),
        "categories": category_chart(df, out_dir),
        "weekdays": weekday_chart(df, out_dir),
        "hours": hourly_chart(df, out_dir),
        "payday": payday_chart(df, out_dir),
        "seasonal": seasonal_chart(df, out_dir),
    }
