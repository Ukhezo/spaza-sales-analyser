"""Spaza Shop Sales Analyser: turn a sales CSV into insights, charts and a report."""

from .analysis import insights, monthly_totals, rand, summarise, top_products
from .data import SalesDataError, load_sales, prepare_sales

__all__ = [
    "SalesDataError",
    "insights",
    "load_sales",
    "monthly_totals",
    "prepare_sales",
    "rand",
    "summarise",
    "top_products",
]
__version__ = "1.1.0"
