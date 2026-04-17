"""
agent.py — SmartAgent: orchestrates scraper selection and the full scrape pipeline.

Flow:
  1. Peek at the URL's raw HTML (first 8 KB)
  2. Ask the LLM which scraper best fits the site
  3. Fall back to can_handle() chain if LLM answer is ambiguous
  4. Run the chosen scraper → ScrapeResult
  5. If endpoints=0 and full text is available → LLM endpoint extraction fallback
  6. Delegate to StorageManager to persist + register the result
"""

import json
import re
import uuid
import requests

from src.llm_client import LLMClient
from src.models import ScrapeResult, AppRecord
from src.tools.base_tool import BaseScraper
from src.tools.bs4_tool import BS4Scraper
from src.tools.scrapy_tool import ScrapyScraper
from src.tools.selenium_tool import SeleniumScraper
from src.tools.octoparse_tool import OctoparseScraper

# Registry of available scrapers in priority order (most-specific first)
SCRAPERS: list[BaseScraper] = [
    OctoparseScraper(),
    SeleniumScraper(),
    ScrapyScraper(),
    BS4Scraper(),
]

TOOL_NAMES = ["beautifulsoup", "scrapy", "selenium", "octoparse"]

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]


class SmartAgent:
    """
    Main orchestration agent.  Create one instance; call run() per URL.
    """

    def __init__(self):
        self.llm = LLMClient()

    # ── Public API ────────────────────────────────────────────────────

    def run(self, url: str, app_name: str) -> tuple[ScrapeResult, AppRecord]:
        """
        Full pipeline: peek → select tool → scrape → fallback cascade → save.

        Fallback cascade (applied when primary tool yields empty endpoints):
          1. If primary tool errored → retry with BS4
          2. If endpoints=0 and URL looks like a multi-page docs site → Scrapy crawl
          3. If still 0 endpoints → LLM extraction from raw text
          4. If still no auth → LLM extraction from raw text
        """
        from src.storage import StorageManager  # local import avoids circular dep

        app_id = self._generate_id(app_name)
        html_hint = self._peek_html(url)
        tool = self._select_tool(url, html_hint)

        result = tool.scrape(url, app_name)

        # ── Fallback 1: chosen tool errored → retry with BS4 ──────────────
        if result.error and tool.name != "beautifulsoup":
            bs4_result = BS4Scraper().scrape(url, app_name)
            if not bs4_result.error:
                result = bs4_result

        # ── Fallback 2: 0 endpoints on a docs URL → Scrapy multi-page crawl ─
        if not result.endpoints and not result.error:
            if ScrapyScraper().can_handle(url) and tool.name != "scrapy":
                scrapy_result = ScrapyScraper().scrape(url, app_name)
                if scrapy_result.endpoints:  # only adopt if we actually got more
                    result = scrapy_result

        # ── Fallback 3: still 0 endpoints → LLM extraction from raw text ───
        if not result.endpoints:
            llm_endpoints = self._llm_extract_endpoints(result)
            if llm_endpoints:
                result.endpoints = llm_endpoints

        # ── Fallback 4: no auth → LLM extraction from raw text ──────────
        if not result.auth_methods:
            llm_auth = self._llm_extract_auth(result)
            if llm_auth:
                result.auth_methods = llm_auth

        storage = StorageManager()
        record = storage.save(result, app_id)

        return result, record

    def select_tool_only(self, url: str) -> str:
        """Lightweight helper — returns the tool name without scraping."""
        html_hint = self._peek_html(url)
        tool = self._select_tool(url, html_hint)
        return tool.name

    # ── Private helpers ───────────────────────────────────────────────

    def _generate_id(self, app_name: str) -> str:
        short = uuid.uuid4().hex[:8]
        slug = re.sub(r"[^a-z0-9]", "", app_name.lower())[:12]
        return f"{short}_{slug}"

    def _peek_html(self, url: str) -> str:
        """Fetch the first 8 KB of a page's HTML for tool-selection hints."""
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            }
            resp = requests.get(url, headers=headers, timeout=10, stream=True)
            resp.raise_for_status()
            raw = b""
            for chunk in resp.iter_content(chunk_size=1024):
                raw += chunk
                if len(raw) >= 8192:
                    break
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _select_tool(self, url: str, html_hint: str) -> BaseScraper:
        """Ask the LLM which scraper to use, then validate + fall back."""
        chosen_name = self._ask_llm_for_tool(url, html_hint)
        if chosen_name:
            for scraper in SCRAPERS:
                if scraper.name == chosen_name:
                    return scraper

        # Fallback: first scraper whose can_handle() is True
        for scraper in SCRAPERS:
            if scraper.can_handle(url, html_hint):
                return scraper

        return BS4Scraper()

    def _ask_llm_for_tool(self, url: str, html_hint: str) -> str | None:
        """
        Returns one of the TOOL_NAMES strings, or None if unclear.
        Uses LLM to intelligently select the best tool for the given site.
        """
        snippet = html_hint[:3000] if html_hint else "(no HTML available)"
        prompt = (
            f"You are a web-scraping expert. Pick the best tool for this site.\n\n"
            f"URL: {url}\n\n"
            f"HTML snippet (first 3000 chars):\n{snippet}\n\n"
            f"Choose exactly one tool from this list: {TOOL_NAMES}.\n"
            f"Rules:\n"
            f"  - Use 'selenium' ONLY if HTML has JS framework signals (__NEXT_DATA__, react-root, ng-app, __NUXT__, vue-app) "
            f"AND there is very little readable text in the HTML.\n"
            f"  - Use 'scrapy' if the URL is a multi-page doc site (/docs/, /reference/, developer.).\n"
            f"  - Use 'octoparse' if the URL involves login/dashboard/portal/console.\n"
            f"  - Use 'beautifulsoup' for plain static HTML or when the page has readable content even with JS.\n\n"
            f'Respond with ONLY valid JSON: {{"tool": "<name>"}}'
        )
        try:
            raw = self.llm.ask_json(prompt)
            raw = re.sub(r"```[a-z]*\n?", "", raw).strip().strip("`")
            data = json.loads(raw)
            candidate = data.get("tool", "").strip().lower()
            if candidate in TOOL_NAMES:
                return candidate
        except Exception:
            pass
        return None

    # ── LLM-powered extraction fallbacks ─────────────────────────────

    def _get_text_context(self, result: ScrapeResult) -> str:
        """Pull the best available text from a ScrapeResult for LLM prompts."""
        # Prefer __full_text__ if present
        if "__full_text__" in result.raw_sections:
            return result.raw_sections["__full_text__"][:5000]
        # Otherwise concatenate regular sections
        parts = []
        for k, v in result.raw_sections.items():
            if not k.startswith("__") and v:
                parts.append(f"## {k}\n{v}")
            if sum(len(p) for p in parts) > 4000:
                break
        return "\n\n".join(parts)[:5000]

    def _llm_extract_endpoints(self, result: ScrapeResult) -> list[dict]:
        """
        Ask the LLM to identify API endpoints from raw page text.
        Returns a list of {method, path, description} dicts or [].
        """
        context = self._get_text_context(result)
        if not context.strip():
            return []

        prompt = (
            f"You are an API documentation parser.\n"
            f"Below is text scraped from the API documentation of '{result.app_name}'.\n"
            f"Extract ALL API endpoints you can find.\n\n"
            f"TEXT:\n{context}\n\n"
            f"Return a JSON array of objects. Each object must have:\n"
            f'  "method": one of GET/POST/PUT/PATCH/DELETE\n'
            f'  "path": the URL path (must start with /)\n'
            f'  "description": one sentence summary\n\n'
            f"If no endpoints exist in the text, return [].\n"
            f"Respond with ONLY the JSON array, no markdown."
        )
        try:
            raw = self.llm.ask_json(prompt)
            raw = re.sub(r"```[a-z]*\n?", "", raw).strip().strip("`")
            data = json.loads(raw)
            if not isinstance(data, list):
                return []
            endpoints = []
            for item in data:
                if isinstance(item, dict):
                    method = str(item.get("method", "")).upper()
                    path = str(item.get("path", ""))
                    desc = str(item.get("description", ""))
                    if method in HTTP_METHODS and path.startswith("/"):
                        endpoints.append(
                            {"method": method, "path": path, "description": desc}
                        )
            return endpoints[:30]
        except Exception:
            return []

    def _llm_extract_auth(self, result: ScrapeResult) -> list[dict]:
        """
        Ask the LLM to identify authentication methods from raw page text.
        Returns a list of {type, description} dicts or [].
        """
        context = self._get_text_context(result)
        if not context.strip():
            return []

        prompt = (
            f"You are an API documentation parser.\n"
            f"Below is text from the docs of '{result.app_name}'.\n"
            f"Identify all authentication/authorization methods described.\n\n"
            f"TEXT:\n{context}\n\n"
            f"Return a JSON array of objects. Each must have:\n"
            f'  "type": e.g. "API Key", "OAuth 2.0", "Bearer Token", "Basic Auth", "JWT"\n'
            f'  "description": how to use it (one sentence)\n\n'
            f"If no auth method is found, return [].\n"
            f"Respond with ONLY the JSON array, no markdown."
        )
        try:
            raw = self.llm.ask_json(prompt)
            raw = re.sub(r"```[a-z]*\n?", "", raw).strip().strip("`")
            data = json.loads(raw)
            if not isinstance(data, list):
                return []
            return [
                {
                    "type": str(i.get("type", "")),
                    "description": str(i.get("description", "")),
                }
                for i in data
                if isinstance(i, dict) and i.get("type")
            ][:5]
        except Exception:
            return []
