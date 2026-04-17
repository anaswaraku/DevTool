import time
from bs4 import BeautifulSoup

from src.models import ScrapeResult
from src.tools.base_tool import BaseScraper
from src.tools.bs4_tool import BS4Scraper, JS_SIGNALS


class SeleniumScraper(BaseScraper):
    name = "selenium"

    def can_handle(self, url: str, html_hint: str = "") -> bool:
        return any(signal in html_hint for signal in JS_SIGNALS)

    def scrape(self, url: str, app_name: str) -> ScrapeResult:
        try:
            html = self._fetch_rendered(url)
            raw_soup = BeautifulSoup(html, "html.parser")
            soup = BS4Scraper()._clean(BeautifulSoup(html, "html.parser"))
            parser = BS4Scraper()

            sections = parser._extract_sections(soup)
            ft = parser._full_text(soup)
            if ft:
                sections["__full_text__"] = ft

            return ScrapeResult(
                url=url,
                app_name=app_name,
                tool_used=self.name,
                endpoints=parser._extract_endpoints(soup, raw_soup),
                auth_methods=parser._extract_auth(soup),
                sample_urls=parser._extract_sample_urls(soup),
                use_cases=parser._extract_use_cases(soup),
                wrapper_hints=parser._extract_snippets(soup),
                raw_sections=sections,
            )
        except ImportError:
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
                error="Selenium not installed. Run: pip install selenium webdriver-manager",
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

    def _fetch_rendered(self, url: str) -> str:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("user-agent=Mozilla/5.0 (research-bot/1.0)")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )

        try:
            driver.get(url)
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)  # let JS finish rendering
            return driver.page_source
        finally:
            driver.quit()  # always close, even on error
