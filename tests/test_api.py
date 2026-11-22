"""Tests for the FastAPI web API, run against the sample data."""

import pytest
from fastapi.testclient import TestClient

from spaza_analyser.api import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_summary_matches_report(client):
    s = client.get("/summary").json()
    assert s["revenue"] == pytest.approx(1_492_200.89)
    assert s["profit"] == pytest.approx(286_606.19)
    assert s["margin_pct"] == 19.2
    assert s["trading_days"] == 365


def test_top_products(client):
    rows = client.get("/products/top", params={"n": 3, "by": "profit"}).json()
    assert len(rows) == 3
    assert rows[0]["product"] == "White bread loaf"
    assert rows[0]["profit"] >= rows[1]["profit"] >= rows[2]["profit"]


def test_top_products_rejects_bad_values(client):
    assert client.get("/products/top", params={"by": "colour"}).status_code == 422
    assert client.get("/products/top", params={"n": 0}).status_code == 422


@pytest.mark.parametrize(
    "path, label",
    [
        ("/monthly", "month"),
        ("/categories", "category"),
        ("/patterns/weekdays", "weekday"),
        ("/patterns/hours", "hour"),
        ("/patterns/payday", "period"),
        ("/payments", "payment_method"),
    ],
)
def test_tables_have_labels(client, path, label):
    rows = client.get(path).json()
    assert rows, f"{path} returned no rows"
    assert all(label in row for row in rows)


def test_payday_effect(client):
    rows = {r["period"]: r["avg_daily_revenue"] for r in client.get("/patterns/payday").json()}
    lift = rows["Payday (25th-3rd)"] / rows["Rest of month"] - 1
    assert lift == pytest.approx(0.68, abs=0.01)


def test_insights(client):
    found = client.get("/insights").json()["insights"]
    assert any("Payday" in line for line in found)


def test_analyse_upload(client):
    csv = (
        "receipt_id,timestamp,product,category,quantity,unit_price,unit_cost,payment_method\n"
        "R1,2025-03-26 07:10,Bread,Bakery,2,20,16,Cash\n"
        "R2,2025-03-14 12:00,Maize 5kg,Groceries,1,75,63,Card\n"
    )
    r = client.post("/analyse", files={"file": ("sales.csv", csv, "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["revenue"] == 115.0
    assert body["top_products"][0]["product"] == "Maize 5kg"


def test_analyse_rejects_bad_file(client):
    r = client.post("/analyse", files={"file": ("bad.csv", "name,price\nbread,20\n", "text/csv")})
    assert r.status_code == 422
    assert "Missing columns" in r.json()["detail"]


def test_chat(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post("/chat", json={"question": "Does payday matter?"})
    assert r.status_code == 200
    body = r.json()
    assert body["topic"] == "payday"
    assert "68%" in body["answer"]


def test_chat_rejects_empty_question(client):
    assert client.post("/chat", json={"question": ""}).status_code == 422


def test_chat_page(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Spaza Sales Chatbot" in r.text
