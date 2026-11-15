"""Generate a year of realistic, fictional sales data for a spaza shop.

The data is synthetic but follows patterns real township shops see:
- busier weekends and month-end / payday spikes (25th to the 3rd)
- a December holiday peak and a quieter January
- more paraffin and candles in winter, more cold drinks in summer
- bread and airtime selling every day, bulk staples selling around payday

Usage:
    python scripts/generate_sample_data.py --out data/sales_2025.csv --seed 42
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# name, category, selling price (R), cost price (R), base daily units
PRODUCTS = [
    ("White bread loaf", "Bread & bakery", 19.99, 16.50, 38),
    ("Brown bread loaf", "Bread & bakery", 17.99, 14.80, 22),
    ("Vetkoek (each)", "Bread & bakery", 5.00, 2.10, 45),
    ("Maize meal 5kg", "Groceries", 74.99, 63.00, 6),
    ("Maize meal 10kg", "Groceries", 139.99, 119.00, 3),
    ("Rice 2kg", "Groceries", 44.99, 37.50, 4),
    ("Sugar 2kg", "Groceries", 46.99, 40.00, 5),
    ("Cooking oil 750ml", "Groceries", 39.99, 33.00, 5),
    ("Tinned pilchards 400g", "Groceries", 29.99, 24.50, 6),
    ("Baked beans 410g", "Groceries", 18.99, 15.20, 6),
    ("Teabags 100s", "Groceries", 49.99, 41.00, 2),
    ("Instant coffee 200g", "Groceries", 64.99, 54.00, 1),
    ("Fresh milk 1L", "Dairy & eggs", 22.99, 19.20, 14),
    ("Maas 2L", "Dairy & eggs", 42.99, 36.00, 4),
    ("Eggs 6s", "Dairy & eggs", 29.99, 24.60, 7),
    ("Cold drink 2L", "Drinks", 27.99, 21.50, 12),
    ("Cold drink 500ml", "Drinks", 13.99, 10.20, 20),
    ("Juice 1L", "Drinks", 24.99, 19.80, 5),
    ("Chips 125g", "Snacks & sweets", 16.99, 12.40, 14),
    ("Sweets (loose)", "Snacks & sweets", 1.00, 0.45, 80),
    ("Biscuits 200g", "Snacks & sweets", 15.99, 11.90, 6),
    ("Paraffin 1L", "Household & energy", 26.99, 21.90, 6),
    ("Candles 6s", "Household & energy", 32.99, 26.00, 4),
    ("Matches 10s", "Household & energy", 12.99, 9.10, 5),
    ("Bath soap", "Household & energy", 14.99, 11.40, 6),
    ("Washing powder 1kg", "Household & energy", 44.99, 37.20, 3),
    ("Toilet paper 4s", "Household & energy", 36.99, 30.10, 4),
    ("Airtime R10", "Airtime & data", 10.00, 9.40, 18),
    ("Airtime R29", "Airtime & data", 29.00, 27.30, 8),
    ("Data 1GB", "Airtime & data", 99.00, 93.00, 3),
]

BULK = {
    "Maize meal 5kg",
    "Maize meal 10kg",
    "Rice 2kg",
    "Sugar 2kg",
    "Cooking oil 750ml",
    "Washing powder 1kg",
    "Teabags 100s",
    "Toilet paper 4s",
    "Instant coffee 200g",
}
WINTER = {"Paraffin 1L", "Candles 6s", "Matches 10s", "Teabags 100s", "Instant coffee 200g"}
SUMMER = {"Cold drink 2L", "Cold drink 500ml", "Juice 1L"}

# Opening hours 06:00 to 20:00, with morning and after-work rushes
HOUR_WEIGHTS = np.array([5, 9, 7, 5, 5, 6, 6, 5, 5, 6, 8, 10, 9, 6], dtype=float)
HOURS = np.arange(6, 20)
PAYMENT_METHODS = ["Cash", "Card", "Mobile wallet"]


def payday_factor(day: date) -> float:
    """Shoppers spend more from the 25th to the 3rd (salaries and grants)."""
    if day.day >= 25 or day.day <= 3:
        return 1.35
    if 4 <= day.day <= 7:
        return 1.10
    return 0.90


def season_factor(product: str, month: int) -> float:
    winter = month in (5, 6, 7, 8)
    summer = month in (11, 12, 1, 2)
    if product in WINTER:
        return 1.8 if winter else 0.8
    if product in SUMMER:
        return 1.5 if summer else 0.8
    return 1.0


def month_factor(month: int) -> float:
    return {1: 0.85, 4: 1.05, 12: 1.30}.get(month, 1.0)


def generate(year: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    receipt = 100000
    day = date(year, 1, 1)
    while day.year == year:
        weekday = day.weekday()
        weekend = 1.25 if weekday >= 5 else (1.1 if weekday == 4 else 1.0)
        for name, category, price, cost, base in PRODUCTS:
            expected = 0.5 * base * weekend * month_factor(day.month) * season_factor(name, day.month)
            expected *= payday_factor(day) ** (2.2 if name in BULK else 1.0)
            units = rng.poisson(expected)
            while units > 0:
                qty = int(min(units, rng.choice([1, 1, 1, 2, 2, 3]) if price < 20 else 1))
                hour = int(rng.choice(HOURS, p=HOUR_WEIGHTS / HOUR_WEIGHTS.sum()))
                minute = int(rng.integers(0, 60))
                pay_p = [0.62, 0.23, 0.15] if price * qty < 60 else [0.45, 0.38, 0.17]
                rows.append(
                    {
                        "timestamp": datetime(day.year, day.month, day.day, hour, minute),
                        "product": name,
                        "category": category,
                        "quantity": qty,
                        "unit_price": price,
                        "unit_cost": cost,
                        "payment_method": rng.choice(PAYMENT_METHODS, p=pay_p),
                    }
                )
                units -= qty
        day += timedelta(days=1)

    df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    df.insert(0, "receipt_id", [f"R{receipt + i}" for i in range(len(df))])
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="data/sales_2025.csv", help="where to write the CSV")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = generate(args.year, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {len(df):,} sales lines to {out}")


if __name__ == "__main__":
    main()
