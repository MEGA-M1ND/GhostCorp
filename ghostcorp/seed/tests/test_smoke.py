"""Baseline smoke tests — guarantee the product is always runnable and green.

The QA agent appends feature tests alongside these; these never get removed, so
a regression that breaks the app's boot is caught immediately.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_index_serves_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "<html" in r.text.lower()


def test_product_info():
    r = client.get("/api/product")
    assert r.status_code == 200
    assert "name" in r.json()
