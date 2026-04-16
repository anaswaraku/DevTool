import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import GROQ_API_KEY, GROQ_API_KEY, LLM_MODEL, DATA_DIR, OUTPUT_DIR
from src.models import ScrapeResult, AppRecord
from src.llm_client import LLMClient


def test_config():
    print("── Config ──────────────────────────")
    assert GROQ_API_KEY, "API key missing"
    assert os.path.exists(DATA_DIR), "data/ folder missing"
    assert os.path.exists(OUTPUT_DIR), "outputs/ folder missing"
    print(f"  model   : {LLM_MODEL}")
    print(f"  api key : {GROQ_API_KEY[:12]}...")
    print(f"  data/   : {DATA_DIR}")
    print("  ✓ passed")


def test_models():
    print("── Models ──────────────────────────")
    result = ScrapeResult(
        url="https://example.com",
        app_name="TestApp",
        tool_used="beautifulsoup",
        endpoints=[{"method": "GET", "path": "/users"}],
        auth_methods=[{"type": "API Key"}],
        sample_urls=["https://api.example.com/v1/users"],
        use_cases=["Fetch user list"],
        wrapper_hints=["requests.get(url, headers=headers)"],
        raw_sections={"Overview": "This is a test API."},
    )
    assert result.app_name == "TestApp"
    assert result.error == ""

    record = AppRecord(
        id="abc12345",
        app_name="TestApp",
        url="https://example.com",
        tool_used="beautifulsoup",
        file_path="data/abc12345_testapp.json",
    )
    assert record.id == "abc12345"
    assert record.scraped_at != ""
    print("  ✓ passed")


def test_llm():
    print("── LLM connection ──────────────────")
    client = LLMClient()
    reply = client.ask(
        'Reply with exactly this JSON: {"status": "ok"}',
        system="You are a test assistant. Follow instructions exactly.",
    )
    print(f"  response : {reply.strip()}")
    assert "ok" in reply.lower(), f"Unexpected reply: {reply}"
    print("  ✓ passed")


if __name__ == "__main__":
    print("\n=== Day 1 Smoke Test ===\n")
    test_config()
    test_models()
    test_llm()
    print("\n=== All checks passed — Day 1 complete ✓ ===\n")
