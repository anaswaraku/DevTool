import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from src.models import ScrapeResult
from src.tools.base_tool import BaseScraper

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]

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
            soup = self._clean(BeautifulSoup(html, "html.parser"))

            return ScrapeResult(
                url=url,
                app_name=app_name,
                tool_used=self.name,
                endpoints=self._extract_endpoints(soup),
                auth_methods=self._extract_auth(soup),
                sample_urls=self._extract_sample_urls(soup),
                use_cases=self._extract_use_cases(soup),
                wrapper_hints=self._extract_snippets(soup),
                raw_sections=self._extract_sections(soup),
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

    # ── private helpers ────────────────────────────────────────────

    def _fetch(self, url: str) -> str:
        headers = {"User-Agent": "Mozilla/5.0 (research-bot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.text

    def _clean(self, soup: BeautifulSoup) -> BeautifulSoup:
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        return soup

    def _extract_sections(self, soup: BeautifulSoup) -> dict:
        sections = {}
        for heading in soup.find_all(["h1", "h2", "h3"]):
            title = heading.get_text(strip=True)
            if not title:
                continue
            parts = []
            for sib in heading.find_next_siblings():
                if sib.name in ["h1", "h2", "h3"]:
                    break
                parts.append(sib.get_text(strip=True, separator=" "))
            sections[title] = " ".join(parts)[:1500]
        return sections

    def _extract_endpoints(self, soup: BeautifulSoup) -> list[dict]:
        endpoints = []
        for tag in soup.find_all(["code", "pre", "span", "p"]):
            text = tag.get_text(strip=True)
            for method in HTTP_METHODS:
                if text.startswith(method + " ") or f"`{method} " in text:
                    parts = text.split(method, 1)
                    if len(parts) < 2:
                        continue
                    path = parts[1].strip().split()[0]
                    if path.startswith("/"):
                        endpoints.append(
                            {
                                "method": method,
                                "path": path,
                                "description": "",
                            }
                        )
        return self._dedupe_endpoints(endpoints)[:30]

    def _dedupe_endpoints(self, endpoints: list[dict]) -> list[dict]:
        seen, unique = set(), []
        for ep in endpoints:
            key = f"{ep['method']}:{ep['path']}"
            if key not in seen:
                seen.add(key)
                unique.append(ep)
        return unique

    def _extract_auth(self, soup: BeautifulSoup) -> list[dict]:
        keyword_map = {
            "api key": "API Key",
            "api_key": "API Key",
            "bearer": "Bearer Token",
            "oauth": "OAuth 2.0",
            "basic auth": "Basic Auth",
            "jwt": "JWT",
            "authorization header": "Authorization Header",
        }
        found = {}
        text = soup.get_text().lower()
        for keyword, label in keyword_map.items():
            if keyword in text and label not in found:
                found[label] = {
                    "type": label,
                    "description": f"Detected '{keyword}' in docs",
                }
        return list(found.values())

    def _extract_sample_urls(self, soup: BeautifulSoup) -> list[str]:
        samples = []
        for tag in soup.find_all(["code", "pre"]):
            for word in tag.get_text().split():
                if word.startswith("http") and len(word) > 15:
                    samples.append(word.strip(".,;\"'`"))
        return list(dict.fromkeys(samples))[:10]

    def _extract_use_cases(self, soup: BeautifulSoup) -> list[str]:
        triggers = [
            "you can",
            "allows you",
            "use case",
            "example",
            "enables",
            "integrate",
        ]
        cases = []
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if any(t in text.lower() for t in triggers) and 30 < len(text) < 200:
                cases.append(text)
        return cases[:8]

    def _extract_snippets(self, soup: BeautifulSoup) -> list[str]:
        snippets = []
        for pre in soup.find_all("pre"):
            text = pre.get_text(strip=True)
            if len(text) > 40:
                snippets.append(text[:400])
        return snippets[:6]
