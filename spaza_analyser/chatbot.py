"""A chatbot that answers a shop owner's questions about their sales.

It works in two modes:

* **Rules mode** (default, free, no internet): the question is matched to a topic
  using keywords, and the answer is built from the same analysis functions the
  report uses. Every number comes straight from the data, so it can't make things up.
* **AI mode** (optional): if ``ANTHROPIC_API_KEY`` is set, the question goes to a
  Claude model together with a short "data brief" of the shop's numbers. The model
  is told to answer only from that brief. If the AI call fails for any reason, the
  bot falls back to rules mode.

Unlike a normal function, an AI model can give a different answer each time and can
sound sure while being wrong. That's why AI mode is grounded in the data brief and
why ``tests/test_chatbot.py`` holds a small evaluation set of questions with the
facts each answer must contain.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import pandas as pd

from .analysis import (
    category_breakdown,
    hourly_pattern,
    insights,
    monthly_totals,
    payday_effect,
    payment_mix,
    product_performance,
    rand,
    slow_movers,
    summarise,
    top_products,
    weekday_pattern,
)

DEFAULT_MODEL = "claude-sonnet-5-5"


@dataclass(frozen=True)
class Answer:
    text: str
    topic: str
    mode: str  # "rules" or "ai"


# --- Rules mode -------------------------------------------------------------

def _count(n: float) -> str:
    """Whole numbers with a space as thousands separator: 79 040."""
    return f"{int(n):,}".replace(",", " ")


def _summary(df: pd.DataFrame) -> str:
    s = summarise(df)
    return (
        f"From {s.first_day:%d %B %Y} to {s.last_day:%d %B %Y} the shop sold {_count(s.items_sold)} items for "
        f"{rand(s.revenue)}, with {rand(s.profit)} gross profit ({s.margin_pct:.1f}% margin). "
        f"That's an average of {rand(s.avg_daily_revenue)} a day over {s.trading_days} trading days."
    )


def _best_product(df: pd.DataFrame) -> str:
    top = top_products(df, 3)
    names = ", ".join(f"{r['product']} ({rand(r['profit'])})" for _, r in top.iterrows())
    return f"The products earning the most profit are {names}. {top.iloc[0]['product']} is number one."


def _best_seller(df: pd.DataFrame) -> str:
    top = top_products(df, 3, by="units")
    names = ", ".join(f"{r['product']} ({_count(r['units'])} sold)" for _, r in top.iterrows())
    return f"The best sellers by number of items are {names}."


def _slow(df: pd.DataFrame) -> str:
    slow = slow_movers(df, 3)
    names = ", ".join(f"{r['product']} ({rand(r['profit'])} profit)" for _, r in slow.iterrows())
    return f"The products earning the least are {names}. Consider stocking less of them or changing the price."


def _payday(df: pd.DataFrame) -> str:
    p = payday_effect(df)["avg_daily_revenue"]
    pay, rest = p["Payday (25th-3rd)"], p["Rest of month"]
    lift = (pay / rest - 1) * 100
    return (
        f"Yes. From the 25th to the 3rd the shop averages {rand(pay)} a day, compared with {rand(rest)} "
        f"for the rest of the month: {lift:.0f}% more. Stock up on bulk staples before the 25th."
    )


def _busiest_day(df: pd.DataFrame) -> str:
    w = weekday_pattern(df)["avg_revenue"]
    return (
        f"{w.idxmax()} is the busiest day (about {rand(w.max())} in sales) and "
        f"{w.idxmin()} is the quietest ({rand(w.min())})."
    )


def _busiest_hour(df: pd.DataFrame) -> str:
    h = hourly_pattern(df)["avg_revenue"].sort_values(ascending=False)
    first, second = int(h.index[0]), int(h.index[1])
    return (
        f"The busiest hour is {first:02d}:00, followed by {second:02d}:00. "
        "Restock the shelves and have extra help ready before then."
    )


def _months(df: pd.DataFrame) -> str:
    m = monthly_totals(df)["revenue"]
    best, worst = m.idxmax(), m.idxmin()
    return (
        f"The best month was {best.strftime('%B')} ({rand(m[best])}) and the quietest was "
        f"{worst.strftime('%B')} ({rand(m[worst])}). Sales usually peak in December."
    )


def _categories(df: pd.DataFrame) -> str:
    c = category_breakdown(df)
    top = c.index[0]
    low = c["margin_pct"].idxmin()
    return (
        f"{top} brings in the most sales ({c.loc[top, 'revenue_share_pct']:.0f}% of the total). "
        f"{low} has the thinnest margin ({c.loc[low, 'margin_pct']:.1f}%)."
    )


def _payments(df: pd.DataFrame) -> str:
    p = payment_mix(df)
    parts = ", ".join(f"{m} {row['share_of_value_pct']:.0f}%" for m, row in p.iterrows())
    return f"By value, customers pay with: {parts}."


# Words that appear in many product names or questions and say nothing about which product is meant.
_GENERIC = {"loaf", "each", "loose", "white", "brown", "with", "much", "many", "sell", "sold", "make", "made",
            "does", "what", "which", "when", "have", "that", "this", "from", "most", "best", "worst", "least",
            "product", "products", "item", "items", "sales", "profit", "shop", "customers", "money"}


def _product_lookup(df: pd.DataFrame, question: str) -> str | None:
    """Answer questions that name a product, e.g. 'how much bread did we sell?'."""
    perf = product_performance(df)
    asked = {w.rstrip("s") for w in re.findall(r"[a-z]+", question) if len(w) > 3} - _GENERIC
    if not asked:
        return None

    def matches(name: str) -> bool:
        words = {w.rstrip("s") for w in re.findall(r"[a-z]+", name.lower()) if len(w) > 3} - _GENERIC
        return bool(words & asked)

    hits = perf[perf["product"].map(matches)]
    if hits.empty or len(hits) > 4:  # nothing named, or too vague to be about one product
        return None
    lines = [
        f"{r['product']}: {_count(r['units'])} sold for {rand(r['revenue'])}, "
        f"earning {rand(r['profit'])} profit ({r['margin_pct']:.1f}% margin)."
        for _, r in hits.iterrows()
    ]
    if len(lines) > 1:
        lines.append(f"Together: {_count(hits['units'].sum())} sold, {rand(hits['profit'].sum())} profit.")
    return "\n".join(lines)


def _advice(df: pd.DataFrame) -> str:
    return "Here is what the numbers suggest:\n- " + "\n- ".join(insights(df))


# Topics, checked in order. The first topic with a matching keyword wins.
TOPICS: list[tuple[str, tuple[str, ...], object]] = [
    ("payday", ("payday", "pay day", "month end", "month-end", "salary", "grant", "25th"), _payday),
    ("slow_movers", ("worst", "least", "slow", "not selling", "lowest", "stop selling"), _slow),
    ("best_seller", ("best seller", "best-selling", "sell the most", "most popular", "most sold"), _best_seller),
    ("best_product", ("most profit", "best product", "top product", "biggest earner", "make the most"), _best_product),
    ("busiest_hour", ("hour", "time of day", "what time", "rush"), _busiest_hour),
    ("busiest_day",
     ("busiest day", "quietest day", "weekday", "day of the week", "weekend", "which day"),
     _busiest_day),
    ("months", ("month", "season", "december", "january"), _months),
    ("categories", ("category", "categories", "margin"), _categories),
    ("payments", ("cash", "card", "payment", "pay", "paid", "wallet"), _payments),
    ("advice", ("advice", "recommend", "suggest", "improve", "tips", "what should"), _advice),
    ("summary", ("total", "summary", "overview", "how much", "revenue", "sales", "profit", "how are we"), _summary),
]

HELP = (
    "I can answer questions about the shop's sales, for example: "
    "'What were total sales?', 'Which product makes the most profit?', 'Does payday matter?', "
    "'What is the busiest day?', 'What time is the rush?', 'How do customers pay?', "
    "'Which products are not selling?' or 'Any advice?'"
)


def answer_with_rules(df: pd.DataFrame, question: str) -> Answer:
    q = question.lower().strip()
    if not q or q in {"hi", "hello", "help", "sawubona", "hey"}:
        return Answer(HELP, "help", "rules")
    product = _product_lookup(df, q)
    if product:
        return Answer(product, "product", "rules")
    for topic, keywords, handler in TOPICS:
        if any(k in q for k in keywords):
            return Answer(handler(df), topic, "rules")  # type: ignore[operator]
    return Answer("Sorry, I don't know that one yet. " + HELP, "unknown", "rules")


# --- AI mode ----------------------------------------------------------------

def data_brief(df: pd.DataFrame) -> dict:
    """A compact summary of the shop's numbers that an AI model can answer from."""
    s = summarise(df)

    def table(frame: pd.DataFrame, cols: list[str]) -> list[dict]:
        out = frame.copy()
        if cols[0] not in out.columns:  # the label is in the index, e.g. month or weekday
            out = out.reset_index()
            out = out.rename(columns={out.columns[0]: cols[0]})
        out[cols[0]] = out[cols[0]].astype(str)
        return json.loads(out[cols].round(2).to_json(orient="records"))

    return {
        "period": f"{s.first_day:%Y-%m-%d} to {s.last_day:%Y-%m-%d}",
        "revenue": round(s.revenue, 2),
        "gross_profit": round(s.profit, 2),
        "margin_pct": round(s.margin_pct, 1),
        "items_sold": s.items_sold,
        "trading_days": s.trading_days,
        "products": table(product_performance(df), ["product", "category", "units", "revenue", "profit", "margin_pct"]),
        "months": table(monthly_totals(df), ["month", "revenue", "profit"]),
        "categories": table(category_breakdown(df), ["category", "revenue", "profit", "margin_pct"]),
        "weekdays": table(weekday_pattern(df), ["weekday", "avg_revenue"]),
        "hours": table(hourly_pattern(df), ["hour", "avg_revenue"]),
        "payday": table(payday_effect(df), ["period", "avg_daily_revenue", "days"]),
        "payments": table(payment_mix(df), ["payment_method", "sales", "revenue", "share_of_value_pct"]),
    }


SYSTEM_PROMPT = (
    "You are a helpful assistant for a South African spaza shop owner. Answer questions about the shop's "
    "sales using ONLY the JSON data brief provided. Money is in South African rand: write it like R 1 234.56. "
    "Keep answers to 2-4 short sentences in plain English and end with one practical tip when it helps. "
    "If the brief does not contain the answer, say you don't have that information. Never invent numbers."
)


def answer_with_ai(df: pd.DataFrame, question: str, model: str | None = None) -> Answer:
    import anthropic  # optional dependency: pip install -r requirements-ai.txt

    client = anthropic.Anthropic()
    reply = client.messages.create(
        model=model or os.environ.get("SPAZA_AI_MODEL", DEFAULT_MODEL),
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Data brief:\n{json.dumps(data_brief(df))}\n\nQuestion: {question}",
        }],
    )
    text = "".join(block.text for block in reply.content if getattr(block, "type", "") == "text").strip()
    return Answer(text, "ai", "ai")


def ask(df: pd.DataFrame, question: str) -> Answer:
    """Answer a question, using AI mode when an API key is set and rules mode otherwise."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return answer_with_ai(df, question)
        except Exception:  # noqa: BLE001 - any AI failure falls back to the reliable rules
            pass
    return answer_with_rules(df, question)
