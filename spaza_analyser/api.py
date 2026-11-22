"""A FastAPI web API for the spaza sales analysis.

Run it locally with:

    uvicorn spaza_analyser.api:app --reload

then open http://127.0.0.1:8000 for the chatbot page or http://127.0.0.1:8000/docs
for interactive API documentation.

The sales file it serves is set with the SPAZA_DATA environment variable
(default: data/sales_2025.csv).
"""

from __future__ import annotations

import io
import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import __version__
from .analysis import (
    category_breakdown,
    hourly_pattern,
    insights,
    monthly_totals,
    payday_effect,
    payment_mix,
    slow_movers,
    summarise,
    top_products,
    weekday_pattern,
)
from .chatbot import ask
from .data import SalesDataError, load_sales, prepare_sales

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "sales_2025.csv"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

app = FastAPI(
    title="Spaza Sales Analyser API",
    version=__version__,
    description=(
        "Answers a spaza shop owner's questions about their sales: what makes money, "
        "when customers shop and what to stock. All money is in South African rand (ZAR)."
    ),
)


@lru_cache(maxsize=1)
def get_sales() -> pd.DataFrame:
    """Load the sales file once and reuse it for every request."""
    return load_sales(os.environ.get("SPAZA_DATA", DEFAULT_DATA))


def records(frame: pd.DataFrame, label: str | None = None) -> list[dict]:
    """Turn an analysis table into JSON-friendly rows, rounding money to cents."""
    out = frame.copy()
    if label and label not in out.columns:
        out = out.reset_index()
        out = out.rename(columns={out.columns[0]: label})
        out[label] = out[label].astype(str)
    out = out.round(2)
    return out.astype(object).where(out.notna(), None).to_dict(orient="records")


def summary_dict(df: pd.DataFrame) -> dict:
    s = summarise(df)
    return {
        "first_day": f"{s.first_day:%Y-%m-%d}",
        "last_day": f"{s.last_day:%Y-%m-%d}",
        "revenue": round(s.revenue, 2),
        "cost": round(s.cost, 2),
        "profit": round(s.profit, 2),
        "margin_pct": round(s.margin_pct, 1),
        "sales_lines": s.sales_lines,
        "items_sold": s.items_sold,
        "trading_days": s.trading_days,
        "avg_daily_revenue": round(s.avg_daily_revenue, 2),
    }


# --- Endpoints ---------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def chat_page() -> str:
    return (Path(__file__).parent / "static" / "chat.html").read_text(encoding="utf-8")


@app.get("/health", tags=["status"])
def health() -> dict:
    """Check that the API is running."""
    return {"status": "ok", "version": __version__}


@app.get("/summary", tags=["sales"])
def summary() -> dict:
    """Headline numbers: sales, profit, margin and items sold."""
    return summary_dict(get_sales())


@app.get("/insights", tags=["sales"])
def get_insights() -> dict:
    """Plain-language findings a shop owner can act on."""
    return {"insights": insights(get_sales())}


@app.get("/monthly", tags=["sales"])
def monthly() -> list[dict]:
    """Revenue, profit and margin for each month."""
    return records(monthly_totals(get_sales()), "month")


@app.get("/products/top", tags=["products"])
def products_top(
    n: int = Query(10, ge=1, le=100, description="How many products to return"),
    by: Literal["profit", "revenue", "units"] = Query("profit", description="What to rank by"),
) -> list[dict]:
    """The best products, ranked by profit, revenue or units sold."""
    return records(top_products(get_sales(), n, by))


@app.get("/products/slow", tags=["products"])
def products_slow(n: int = Query(5, ge=1, le=100)) -> list[dict]:
    """Products earning the least profit: candidates to stock less or re-price."""
    return records(slow_movers(get_sales(), n))


@app.get("/categories", tags=["sales"])
def categories() -> list[dict]:
    """Revenue, profit and margin by category."""
    return records(category_breakdown(get_sales()), "category")


@app.get("/patterns/weekdays", tags=["patterns"])
def weekdays() -> list[dict]:
    """Average sales for each day of the week."""
    return records(weekday_pattern(get_sales()), "weekday")


@app.get("/patterns/hours", tags=["patterns"])
def hours() -> list[dict]:
    """Average sales for each opening hour."""
    return records(hourly_pattern(get_sales()), "hour")


@app.get("/patterns/payday", tags=["patterns"])
def payday() -> list[dict]:
    """Average daily sales in the payday window (25th to 3rd) compared with the rest of the month."""
    return records(payday_effect(get_sales()), "period")


@app.get("/payments", tags=["sales"])
def payments() -> list[dict]:
    """How customers pay: cash, card or mobile wallet."""
    return records(payment_mix(get_sales()), "payment_method")


class AnalyseResult(BaseModel):
    summary: dict
    insights: list[str]
    top_products: list[dict]


@app.post("/analyse", tags=["your data"], response_model=AnalyseResult)
async def analyse(
    file: Annotated[UploadFile, File(description="A sales CSV in the same format as data/sales_2025.csv")],
) -> AnalyseResult:
    """Upload your own sales CSV and get the headline numbers, insights and top products back."""
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is too large (limit 5 MB)")
    try:
        df = prepare_sales(pd.read_csv(io.BytesIO(raw)))
    except SalesDataError as err:
        raise HTTPException(422, str(err)) from err
    except (pd.errors.ParserError, UnicodeDecodeError, pd.errors.EmptyDataError) as err:
        raise HTTPException(422, "Could not read the file as a CSV") from err
    if df.empty:
        raise HTTPException(422, "The file has no sales rows")
    return AnalyseResult(summary=summary_dict(df), insights=insights(df), top_products=records(top_products(df, 5)))


class Question(BaseModel):
    question: str = Field(..., min_length=1, max_length=500, examples=["Does payday matter?"])


class ChatAnswer(BaseModel):
    answer: str
    topic: str
    mode: str


@app.post("/chat", tags=["chatbot"], response_model=ChatAnswer)
def chat(body: Question) -> ChatAnswer:
    """Ask a question about the shop's sales in plain English."""
    result = ask(get_sales(), body.question)
    return ChatAnswer(answer=result.text, topic=result.topic, mode=result.mode)
