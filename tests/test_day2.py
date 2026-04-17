"""
test_day2.py — Smoke tests for agent.py, storage.py, and query.py
"""

import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models import ScrapeResult, AppRecord
from src.storage import StorageManager
from src.query import QueryEngine


# ── Fixtures ───────────────────────────────────────────────────────────────────

FIXTURE_RESULT = ScrapeResult(
    url="https://httpbin.org/",
    app_name="HTTPBin",
    tool_used="beautifulsoup",
    endpoints=[
        {"method": "GET", "path": "/get", "description": "Returns GET data"},
        {"method": "POST", "path": "/post", "description": "Returns POST data"},
        {"method": "DELETE", "path": "/delete", "description": "Returns DELETE data"},
    ],
    auth_methods=[
        {"type": "Basic Auth", "description": "Detected 'basic auth' in docs"},
        {"type": "Bearer Token", "description": "Detected 'bearer' in docs"},
    ],
    sample_urls=["https://httpbin.org/get", "https://httpbin.org/post"],
    use_cases=["Test HTTP requests", "Inspect headers and body"],
    wrapper_hints=["requests.get('https://httpbin.org/get')"],
    raw_sections={
        "Overview": "HTTPBin allows you to test HTTP methods.",
        "Authentication": "Supports basic auth and bearer tokens.",
    },
)


# ── Test: StorageManager ───────────────────────────────────────────────────────

def test_storage_save_load():
    print("── Storage: save & load ─────────────────────────────")
    storage = StorageManager()
    app_id = "test_0001_httpbin"

    record = storage.save(FIXTURE_RESULT, app_id)
    print(f"  saved  → id={record.id if hasattr(record, 'id') else record['id']}")

    loaded = storage.load(app_id)
    assert loaded["app_name"] == "HTTPBin", f"Expected HTTPBin, got {loaded['app_name']}"
    assert loaded["tool_used"] == "beautifulsoup"
    assert len(loaded["endpoints"]) == 3
    print("  ✓ save & load passed")

    # Cleanup
    storage.delete(app_id)
    print("  ✓ delete passed")


def test_storage_registry():
    print("── Storage: registry list ──────────────────────────")
    storage = StorageManager()
    app_id = "test_0002_httpbin"

    storage.save(FIXTURE_RESULT, app_id)
    apps = storage.list_apps()
    ids = [a["id"] for a in apps]
    assert app_id in ids, f"{app_id} not in registry: {ids}"
    print(f"  registry has {len(apps)} app(s), includes our test record ✓")

    storage.delete(app_id)
    apps_after = storage.list_apps()
    ids_after = [a["id"] for a in apps_after]
    assert app_id not in ids_after, "Record should be gone after delete"
    print("  ✓ delete removes from registry")


# ── Test: QueryEngine ─────────────────────────────────────────────────────────

def test_query_engine():
    print("── QueryEngine: LLM answer ─────────────────────────")
    from dataclasses import asdict

    engine = QueryEngine()
    app_data = asdict(FIXTURE_RESULT)

    answer = engine.answer(app_data, "What HTTP methods does this API support?")
    print(f"  Q: What HTTP methods does this API support?")
    print(f"  A: {answer[:300]}")
    assert len(answer) > 10, "LLM returned empty answer"
    assert any(m in answer.upper() for m in ["GET", "POST", "DELETE"]), (
        "Expected at least one HTTP method in the answer"
    )
    print("  ✓ query engine passed")


# ── Test: Agent tool selection (no network) ────────────────────────────────────

def test_agent_tool_selection_static():
    print("── Agent: can_handle() fallback ────────────────────")
    from src.tools.bs4_tool import BS4Scraper
    from src.tools.scrapy_tool import ScrapyScraper
    from src.tools.selenium_tool import SeleniumScraper
    from src.tools.octoparse_tool import OctoparseScraper

    # Plain HTML → BS4
    bs4 = BS4Scraper()
    assert bs4.can_handle("https://example.com", "<html><body>Hello</body></html>")
    assert not bs4.can_handle("", "__NEXT_DATA__")
    print("  BS4Scraper.can_handle ✓")

    # Docs URL → Scrapy
    scrapy = ScrapyScraper()
    assert scrapy.can_handle("https://docs.stripe.com/api/")
    assert not scrapy.can_handle("https://stripe.com/home")
    print("  ScrapyScraper.can_handle ✓")

    # JS signal → Selenium
    sel = SeleniumScraper()
    assert sel.can_handle("", "__NEXT_DATA__")
    assert not sel.can_handle("https://docs.example.com", "<html></html>")
    print("  SeleniumScraper.can_handle ✓")

    # Login URL → Octoparse
    oct = OctoparseScraper()
    assert oct.can_handle("https://console.aws.amazon.com/login")
    assert not oct.can_handle("https://docs.example.com")
    print("  OctoparseScraper.can_handle ✓")


# ── Runner ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n=== Day 2 Smoke Tests ===\n")
    test_storage_save_load()
    print()
    test_storage_registry()
    print()
    test_agent_tool_selection_static()
    print()
    test_query_engine()
    print("\n=== All Day 2 checks passed ✓ ===\n")
