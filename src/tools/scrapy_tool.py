import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from src.models import ScrapeResult
from src.tools.base_tool import BaseScraper
from src.tools.bs4_tool import BS4Scraper

DOC_SIGNALS = [
    "docs.",
    "/docs/",
    "/api-reference",
    "/reference/",
    "developer.",
    "/developers/",
]


class ScrapyScraper(BaseScraper):
    name = "scrapy"

    def can_handle(self, url: str, html_hint: str = "") -> bool:
        return any(signal in url for signal in DOC_SIGNALS)

    def scrape(self, url: str, app_name: str) -> ScrapeResult:
        try:
            pages = self._crawl(url, max_pages=6)

            parser = BS4Scraper()
            all_sections = {}
            all_endpoints = []
            all_auth = []
            all_samples = []
            all_use_cases = []
            all_snippets = []

            for html in pages:
                raw_soup = BeautifulSoup(html, "html.parser")
                soup = parser._clean(BeautifulSoup(html, "html.parser"))
                all_sections.update(parser._extract_sections(soup))
                all_endpoints.extend(parser._extract_endpoints(soup, raw_soup))
                all_auth.extend(parser._extract_auth(soup))
                all_samples.extend(parser._extract_sample_urls(soup))
                all_use_cases.extend(parser._extract_use_cases(soup))
                all_snippets.extend(parser._extract_snippets(soup))
                # Full-text per page as LLM fallback
                ft = parser._full_text(soup)
                if ft:
                    all_sections[f"__full_text_page_{len(all_sections)}__"] = ft

            return ScrapeResult(
                url=url,
                app_name=app_name,
                tool_used=self.name,
                endpoints=self._dedupe_endpoints(all_endpoints)[:40],
                auth_methods=self._dedupe_auth(all_auth),
                sample_urls=list(dict.fromkeys(all_samples))[:15],
                use_cases=list(dict.fromkeys(all_use_cases))[:10],
                wrapper_hints=all_snippets[:8],
                raw_sections=all_sections,
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

    def _crawl(self, start_url: str, max_pages: int) -> list[str]:
        """
        Breadth-first crawl staying within the same domain.
        Returns raw HTML strings for each visited page.
        """
        headers = {"User-Agent": "Mozilla/5.0 (research-bot/1.0)"}
        domain = urlparse(start_url).netloc
        visited = set()
        queue = [start_url]
        pages = []

        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                html = resp.text
                pages.append(html)

                # discover same-domain links
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = urljoin(url, a["href"])
                    parsed = urlparse(href)
                    if parsed.netloc == domain and href not in visited:
                        queue.append(href)

            except Exception:
                continue  # skip unreachable pages silently

        return pages

    def _dedupe_endpoints(self, endpoints: list[dict]) -> list[dict]:
        seen, unique = set(), []
        for ep in endpoints:
            key = f"{ep['method']}:{ep['path']}"
            if key not in seen:
                seen.add(key)
                unique.append(ep)
        return unique

    def _dedupe_auth(self, auth_list: list[dict]) -> list[dict]:
        return list({a["type"]: a for a in auth_list}.values())
