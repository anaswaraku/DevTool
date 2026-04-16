from abc import ABC, abstractmethod
from src.models import ScrapeResult


class BaseScraper(ABC):
    name: str = "base"

    @abstractmethod
    def can_handle(self, url: str, html_hint: str = "") -> bool:
        """
        Return True if this tool is the right choice for the given URL.
        html_hint is the first 8KB of raw HTML — used to detect JS frameworks.
        """

    @abstractmethod
    def scrape(self, url: str, app_name: str) -> ScrapeResult:
        """
        Scrape the URL and return a structured ScrapeResult.
        Never raise — catch all exceptions and return ScrapeResult with error set.
        """
