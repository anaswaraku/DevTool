import os
import requests

from src.models import ScrapeResult
from src.tools.base_tool import BaseScraper

COMPLEX_SIGNALS = ["login", "signin", "dashboard", "console", "portal"]

NO_TOKEN_NOTE = (
    "Octoparse requires a paid account and OCTOPARSE_TOKEN in your .env. "
    "Visit https://www.octoparse.com, create a task for this URL, "
    "export results as JSON, and place it in data/manual_{app_name}.json."
)


class OctoparseScraper(BaseScraper):
    name = "octoparse"

    def can_handle(self, url: str, html_hint: str = "") -> bool:
        return any(signal in url.lower() for signal in COMPLEX_SIGNALS)

    def scrape(self, url: str, app_name: str) -> ScrapeResult:
        token = os.getenv("OCTOPARSE_TOKEN", "")

        if not token:
            return self._no_token_result(url, app_name)

        try:
            return self._call_api(url, app_name, token)
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

    def _no_token_result(self, url: str, app_name: str) -> ScrapeResult:
        return ScrapeResult(
            url=url,
            app_name=app_name,
            tool_used=self.name,
            endpoints=[],
            auth_methods=[],
            sample_urls=[],
            use_cases=[],
            wrapper_hints=[],
            raw_sections={"note": NO_TOKEN_NOTE},
            error="OCTOPARSE_TOKEN not set — manual extraction required.",
        )

    def _call_api(self, url: str, app_name: str, token: str) -> ScrapeResult:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            "https://openapi.octoparse.com/api/runTask",
            json={"url": url},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        return ScrapeResult(
            url=url,
            app_name=app_name,
            tool_used=self.name,
            endpoints=data.get("endpoints", []),
            auth_methods=data.get("auth", []),
            sample_urls=data.get("examples", []),
            use_cases=data.get("usecases", []),
            wrapper_hints=data.get("code_snippets", []),
            raw_sections=data.get("sections", {}),
        )
