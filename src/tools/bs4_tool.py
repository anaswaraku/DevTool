"""
bs4_tool.py — BeautifulSoup scraper for static HTML API documentation.

Extraction strategy (layered, most reliable → least):
  1. Regex scan of ALL page text for "METHOD /path" patterns
  2. <table> rows pairing a method cell with a path cell
  3. Adjacent sibling elements where one contains a method and next contains a path
  4. <code>/<pre> blocks — multi-line, scan each line
  5. Full-text content preserved in raw_sections for LLM querying
"""

import re
import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin

from src.models import ScrapeResult
from src.tools.base_tool import BaseScraper

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]

# Regex: matches "GET /some/path" with optional trailing chars
_EP_RE = re.compile(
    r"\b(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\b\s{0,4}(/[^\s\"'<>{}\[\]\\^`]{1,120})",
    re.IGNORECASE | re.MULTILINE,
)

# Detects JS-framework signals that mean we need Selenium instead
JS_SIGNALS = [
    "__NEXT_DATA__",
    "react-root",
    "ng-app",
    "__NUXT__",
    "window.__APP__",
    "vue-app",
]


class BS4Scraper(BaseScraper):
    name = "beautifulsoup"

    def can_handle(self, url: str, html_hint: str = "") -> bool:
        return not any(signal in html_hint for signal in JS_SIGNALS)

    def scrape(self, url: str, app_name: str) -> ScrapeResult:
        try:
            html = self._fetch(url)
            # Parse twice: cleaned soup for structured extraction,
            # raw soup for full-text dump (preserves more content for LLM)
            raw_soup = BeautifulSoup(html, "html.parser")
            soup = self._clean(BeautifulSoup(html, "html.parser"))

            endpoints = self._extract_endpoints(soup, raw_soup)
            auth = self._extract_auth(soup)
            samples = self._extract_sample_urls(soup)
            use_cases = self._extract_use_cases(soup)
            snippets = self._extract_snippets(soup)
            sections = self._extract_sections(soup)

            # Always add a full-text chunk so the LLM query layer has something
            # to work with even if structural extraction found nothing
            full_text = self._full_text(soup)
            if full_text:
                sections["__full_text__"] = full_text

            return ScrapeResult(
                url=url,
                app_name=app_name,
                tool_used=self.name,
                endpoints=endpoints,
                auth_methods=auth,
                sample_urls=samples,
                use_cases=use_cases,
                wrapper_hints=snippets,
                raw_sections=sections,
            )
        except Exception as e:
            return ScrapeResult(
                url=url,
                app_name=app_name,
                tool_used=self.name,
                endpoints=[],
                auth_methods=[],
                sample_urls=[],
                use_cases=[],
                wrapper_hints=[],
                raw_sections={},
                error=str(e),
            )

    # ── Fetch ──────────────────────────────────────────────────────────────────

    def _fetch(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.text

    # ── Clean ─────────────────────────────────────────────────────────────────

    def _clean(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Remove chrome (nav, footer, ads) but keep all content tags."""
        for tag in soup(
            [
                "script",
                "style",
                "nav",
                "footer",
                "header",
                "aside",
                "noscript",
                "iframe",
                "svg",
            ]
        ):
            tag.decompose()
        return soup

    # ── Endpoint extraction ────────────────────────────────────────────────────

    def _extract_endpoints(
        self, soup: BeautifulSoup, raw_soup: BeautifulSoup
    ) -> list[dict]:
        endpoints: list[dict] = []

        # ── Strategy 1: <code> and <pre> blocks, line-by-line ─────────────────
        # Extract from code blocks FIRST to avoid duplicates with Strategy 2
        # "curl -X POST https://api.example.com/v1/users" → extract path
        code_block_endpoints = set()  # track (method, path) pairs from code blocks
        for tag in soup.find_all(["code", "pre"]):
            text = tag.get_text(" ", strip=True)
            for m in _EP_RE.finditer(text):
                method = m.group(1).upper()
                path = m.group(2).rstrip(".,;:)>]}")
                if len(path) > 1:
                    key = f"{method}:{path}"
                    if key not in code_block_endpoints:
                        code_block_endpoints.add(key)
                        endpoints.append(
                            {"method": method, "path": path, "description": ""}
                        )

            # Also catch curl commands: curl -X POST https://host/path
            for line in text.splitlines():
                curl_match = re.search(
                    r"curl\s+(?:-X\s+)?(\w+)\s+https?://[^\s/]+(/[^\s\"']*)",
                    line,
                    re.IGNORECASE,
                )
                if curl_match:
                    method_raw = curl_match.group(1).upper()
                    path = curl_match.group(2).rstrip(".,;:'\")")
                    if method_raw in HTTP_METHODS and len(path) > 1:
                        key = f"{method_raw}:{path}"
                        if key not in code_block_endpoints:
                            code_block_endpoints.add(key)
                            endpoints.append(
                                {"method": method_raw, "path": path, "description": ""}
                            )

        # ── Strategy 2: Regex over the page text (excluding code blocks) ──────
        # Get full text but skip code/pre blocks that we already extracted
        soup_copy = BeautifulSoup(str(soup), "html.parser")
        for tag in soup_copy(["code", "pre"]):
            tag.decompose()
        full_text = soup_copy.get_text(" ", strip=True)

        for m in _EP_RE.finditer(full_text):
            method = m.group(1).upper()
            path = m.group(2).rstrip(".,;:)>]}")
            if len(path) > 1:
                key = f"{method}:{path}"
                if key not in code_block_endpoints:
                    endpoints.append(
                        {"method": method, "path": path, "description": ""}
                    )

        # ── Strategy 3: Table rows (method col + path col) ────────────────────
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                method, path = None, None
                for cell in cells:
                    cell_upper = cell.upper().strip()
                    if cell_upper in HTTP_METHODS:
                        method = cell_upper
                    elif cell.startswith("/") and " " not in cell.strip():
                        path = cell.strip()
                if method and path:
                    endpoints.append(
                        {"method": method, "path": path, "description": ""}
                    )

        # ── Strategy 4: Adjacent sibling elements ─────────────────────────────
        # e.g. <span class="method">GET</span><span class="path">/users</span>
        for tag in soup.find_all(True):
            text = tag.get_text(strip=True).upper()
            if text in HTTP_METHODS:
                sibling = tag.find_next_sibling()
                if sibling:
                    sib_text = sibling.get_text(strip=True)
                    if sib_text.startswith("/") and len(sib_text) > 1:
                        endpoints.append(
                            {
                                "method": text,
                                "path": sib_text.split()[0].rstrip(".,;:)"),
                                "description": "",
                            }
                        )

        deduped = self._dedupe_endpoints(endpoints)

        # Attach descriptions from nearby text for any found endpoint
        deduped = self._enrich_descriptions(deduped, soup)

        return deduped[:40]

    def _enrich_descriptions(
        self, endpoints: list[dict], soup: BeautifulSoup
    ) -> list[dict]:
        """
        For each endpoint, try to find a descriptive nearby element.
        Searches in order: method+path in table cells, nearby headers, semantic elements.
        Best-effort: leaves description empty if nothing found.
        """
        for ep in endpoints:
            method = ep["method"]
            path = ep["path"]
            desc = self._find_endpoint_description(soup, method, path)
            if desc:
                ep["description"] = desc[:100]
        return endpoints

    def _find_endpoint_description(
        self, soup: BeautifulSoup, method: str, path: str
    ) -> str:
        """
        Search for a description of an endpoint by looking in structured elements.
        """
        # Strategy 1: Check table cells with method+path pattern
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                row_text = " ".join(cell.get_text(strip=True) for cell in cells)
                if method in row_text and path in row_text:
                    # Look for adjacent cells that might be description
                    for i, cell in enumerate(cells):
                        cell_text = cell.get_text(strip=True)
                        if path in cell_text or method in cell_text:
                            # Check next cell or nearby cells for description
                            for j in range(i + 1, min(i + 3, len(cells))):
                                desc = cells[j].get_text(strip=True)
                                if (
                                    desc
                                    and len(desc) > 10
                                    and not desc.startswith(method)
                                ):
                                    return desc

        # Strategy 2: Look for method+path in <code>, <pre>, or <li>
        # and find a nearby paragraph or heading
        for tag in soup.find_all(["code", "pre", "li", "span"]):
            text = tag.get_text(strip=True)
            if method in text and path in text:
                # Search parent chain for description text
                parent = tag.parent
                for _ in range(3):  # up to 3 levels up
                    if parent is None:
                        break
                    # Look for sibling paragraphs or previous elements
                    for sibling in parent.find_all(["p", "div"], recursive=False):
                        sibling_text = sibling.get_text(strip=True)
                        if sibling_text and len(sibling_text) > 15:
                            if not any(m in sibling_text.upper() for m in HTTP_METHODS):
                                return sibling_text
                    parent = parent.parent

        # Strategy 3: Search for preceding header + path pattern
        for tag in soup.find_all(True):
            text = tag.get_text(strip=True)
            if path in text and len(text) < 200:
                # Find nearest preceding header
                current = tag
                for _ in range(5):  # search up to 5 levels
                    prev_sibling = current.find_previous_sibling(
                        ["h1", "h2", "h3", "h4"]
                    )
                    if prev_sibling:
                        header_text = prev_sibling.get_text(strip=True)
                        if header_text and len(header_text) > 5:
                            return header_text
                    current = current.parent
                    if current is None:
                        break

        # Strategy 4: Last resort - grab surrounding text from full document
        page_text = soup.get_text(" ", strip=True)
        # Find path and get context before and after (avoid duplicates with another method)
        idx = page_text.find(path)
        if idx != -1 and idx > 50:
            # Get text before the path (better for descriptions)
            before = page_text[max(0, idx - 80) : idx]
            desc = before.split()[-5:] if before.split() else []
            if desc:
                return " ".join(desc)

        return ""

    def _dedupe_endpoints(self, endpoints: list[dict]) -> list[dict]:
        seen: set[str] = set()
        unique: list[dict] = []
        for ep in endpoints:
            key = f"{ep['method']}:{ep['path']}"
            if key not in seen:
                seen.add(key)
                unique.append(ep)
        return unique

    # ── Auth extraction ────────────────────────────────────────────────────────

    def _extract_auth(self, soup: BeautifulSoup) -> list[dict]:
        keyword_map = {
            "api key": "API Key",
            "api_key": "API Key",
            "x-api-key": "API Key",
            "bearer": "Bearer Token",
            "oauth 2": "OAuth 2.0",
            "oauth2": "OAuth 2.0",
            "basic auth": "Basic Auth",
            "authorization: basic": "Basic Auth",
            "jwt": "JWT",
            "json web token": "JWT",
            "authorization header": "Authorization Header",
            "token-based": "Token Auth",
            "api token": "API Token",
            "hmac": "HMAC Signature",
        }
        found: dict[str, dict] = {}
        text = soup.get_text().lower()
        for keyword, label in keyword_map.items():
            if keyword in text and label not in found:
                # Find the sentence containing this keyword for context
                idx = text.find(keyword)
                snippet = text[max(0, idx - 30) : idx + 120]
                snippet = re.sub(r"\s+", " ", snippet).strip()
                found[label] = {
                    "type": label,
                    "description": f"Detected: …{snippet}…",
                }
        return list(found.values())

    # ── Sample URLs ────────────────────────────────────────────────────────────

    def _extract_sample_urls(self, soup: BeautifulSoup) -> list[str]:
        samples: list[str] = []

        # From <a href> links that look like API calls
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and any(
                seg in href for seg in ["/api/", "/v1/", "/v2/", "/v3/"]
            ):
                samples.append(href.rstrip(".,;\"'`"))

        # From code/pre blocks
        for tag in soup.find_all(["code", "pre"]):
            for word in tag.get_text().split():
                if word.startswith("http") and len(word) > 15 and "/" in word[8:]:
                    samples.append(word.strip(".,;\"'`"))

        # From raw text (https://... patterns)
        url_re = re.compile(r"https?://[^\s\"'<>]{16,}")
        for m in url_re.finditer(soup.get_text()):
            samples.append(m.group(0).rstrip(".,;:)\"'`"))

        return list(dict.fromkeys(samples))[:15]

    # ── Use cases ─────────────────────────────────────────────────────────────

    def _extract_use_cases(self, soup: BeautifulSoup) -> list[str]:
        triggers = [
            "you can",
            "allows you",
            "use case",
            "example",
            "enables",
            "integrate",
            "retrieve",
            "create",
            "update",
            "delete",
            "manage",
            "lets you",
            "used to",
            "this endpoint",
            "this api",
        ]
        cases: list[str] = []
        for p in soup.find_all(["p", "li"]):
            text = p.get_text(strip=True)
            if any(t in text.lower() for t in triggers) and 40 < len(text) < 250:
                cases.append(text)
        # Dedupe preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for c in cases:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique[:10]

    # ── Code snippets ─────────────────────────────────────────────────────────

    def _extract_snippets(self, soup: BeautifulSoup) -> list[str]:
        snippets: list[str] = []
        for pre in soup.find_all(["pre", "code"]):
            text = pre.get_text(strip=True)
            # Only keep substantial blocks (not one-liners or tiny badges)
            if 60 < len(text) < 2000:
                snippets.append(text[:500])
        # Dedupe
        seen: set[str] = set()
        unique: list[str] = []
        for s in snippets:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        return unique[:8]

    # ── Sections (for LLM context) ────────────────────────────────────────────

    def _extract_sections(self, soup: BeautifulSoup) -> dict:
        sections: dict[str, str] = {}
        for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
            title = heading.get_text(strip=True)
            if not title or len(title) > 120:
                continue
            parts: list[str] = []
            for sib in heading.find_next_siblings():
                if sib.name in ["h1", "h2", "h3", "h4"]:
                    break
                if isinstance(sib, Tag):
                    parts.append(sib.get_text(strip=True, separator=" "))
            content = " ".join(parts).strip()
            if content:
                sections[title] = content[:2000]
        return sections

    def _full_text(self, soup: BeautifulSoup) -> str:
        """
        Returns a cleaned dump of all visible text — used as a catch-all
        context block for the LLM query layer when structured extraction
        finds nothing useful.
        """
        text = soup.get_text(separator="\n", strip=True)
        # Collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:8000]
