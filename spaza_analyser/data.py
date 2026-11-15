"""Loading and validating sales data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "receipt_id",
    "timestamp",
    "product",
    "category",
    "quantity",
    "unit_price",
    "unit_cost",
    "payment_method",
]


class SalesDataError(ValueError):
    """Raised when a sales file is missing columns or has bad values."""


def load_sales(path: str | Path) -> pd.DataFrame:
    """Read a sales CSV and return a clean DataFrame with money columns added."""
    path = Path(path)
    if not path.exists():
        raise SalesDataError(f"File not found: {path}")
    df = pd.read_csv(path)
    return prepare_sales(df)


def prepare_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Validate raw sales rows and add revenue, cost, profit and date parts."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise SalesDataError(f"Missing columns: {', '.join(missing)}")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ("quantity", "unit_price", "unit_cost"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    bad = df[["timestamp", "quantity", "unit_price", "unit_cost"]].isna().any(axis=1)
    if bad.any():
        raise SalesDataError(f"{int(bad.sum())} row(s) have an invalid date or number")
    if (df["quantity"] <= 0).any():
        raise SalesDataError("Quantities must be greater than zero")
    if ((df["unit_price"] < 0) | (df["unit_cost"] < 0)).any():
        raise SalesDataError("Prices and costs cannot be negative")

    df["revenue"] = df["quantity"] * df["unit_price"]
    df["cost"] = df["quantity"] * df["unit_cost"]
    df["profit"] = df["revenue"] - df["cost"]
    df["date"] = df["timestamp"].dt.normalize()
    df["month"] = df["timestamp"].dt.to_period("M")
    df["weekday"] = df["timestamp"].dt.day_name()
    df["hour"] = df["timestamp"].dt.hour
    return df.sort_values("timestamp").reset_index(drop=True)
