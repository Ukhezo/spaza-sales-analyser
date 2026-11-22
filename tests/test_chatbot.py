"""Evaluation set for the chatbot.

Each case is a question a shop owner might ask, the topic it should be routed to,
and facts the answer must contain. Rules mode is checked on every push. The same
cases can be run against AI mode with an API key (see test_ai_mode below), which
is how you check that a model answers from the data instead of guessing.
"""

import json
import os

import pytest

from spaza_analyser.chatbot import answer_with_rules, ask, data_brief
from spaza_analyser.data import load_sales

EVAL_CASES = [
    # question, expected topic, facts the answer must contain
    ("What were our total sales?", "summary", ["R 1 492 200.89", "19.2%"]),
    ("Which product makes the most profit?", "best_product", ["White bread loaf"]),
    ("What is our best seller?", "best_seller", ["Sweets (loose)"]),
    ("Does payday matter?", "payday", ["68%"]),
    ("Which is the busiest day of the week?", "busiest_day", ["Sunday"]),
    ("What time is the rush?", "busiest_hour", ["17:00", "07:00"]),
    ("Which month was best?", "months", ["December", "January"]),
    ("How do customers pay?", "payments", ["Cash 58%"]),
    ("Which products are not selling?", "slow_movers", ["Airtime R10"]),
    ("How much bread did we sell?", "product", ["White bread loaf", "Brown bread loaf"]),
    ("How is paraffin doing?", "product", ["Paraffin 1L"]),
    ("Which category has the thinnest margin?", "categories", ["Airtime & data"]),
    ("Any advice?", "advice", ["stock up"]),
    ("hello", "help", ["for example"]),
    ("What is the weather tomorrow?", "unknown", ["don't know"]),
]


@pytest.fixture(scope="module")
def sales():
    return load_sales("data/sales_2025.csv")


@pytest.mark.parametrize("question, topic, facts", EVAL_CASES)
def test_rules_mode(sales, question, topic, facts):
    result = answer_with_rules(sales, question)
    assert result.topic == topic
    for fact in facts:
        assert fact in result.text, f"{fact!r} missing from: {result.text}"


def test_ask_uses_rules_without_api_key(sales, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ask(sales, "Does payday matter?").mode == "rules"


def test_ask_falls_back_to_rules_when_ai_fails(sales, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")

    def broken(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("spaza_analyser.chatbot.answer_with_ai", broken)
    result = ask(sales, "Does payday matter?")
    assert result.mode == "rules"
    assert "68%" in result.text


def test_data_brief_is_json_and_complete(sales):
    brief = data_brief(sales)
    json.dumps(brief)  # must be serialisable to send to the model
    assert brief["revenue"] == pytest.approx(1_492_200.89)
    assert len(brief["products"]) == sales["product"].nunique()
    assert {"months", "weekdays", "hours", "payday", "payments", "categories"} <= brief.keys()


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="needs ANTHROPIC_API_KEY (AI mode)")
@pytest.mark.parametrize("question, topic, facts", [c for c in EVAL_CASES if c[1] not in {"help", "unknown"}])
def test_ai_mode(sales, question, topic, facts):
    from spaza_analyser.chatbot import answer_with_ai

    text = answer_with_ai(sales, question).text
    # AI wording varies, so only check the key names and percentages, not exact rand amounts.
    for fact in facts:
        if not fact.startswith("R "):
            assert fact.split(" ")[0].lower() in text.lower(), f"{fact!r} missing from: {text}"
