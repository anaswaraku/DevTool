"""
tests/test_scrapers_manual.py — Test each scraper individually with manual input.
Run: python tests/test_scrapers_manual.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.tools.bs4_tool import BS4Scraper
from src.tools.scrapy_tool import ScrapyScraper
from src.tools.selenium_tool import SeleniumScraper
from src.tools.octoparse_tool import OctoparseScraper
import json


def print_result(result):
    """Pretty print a ScrapeResult."""
    print("\n" + "=" * 60)
    print(f"App: {result.app_name}")
    print(f"URL: {result.url}")
    print(f"Tool: {result.tool_used}")
    print("=" * 60)

    if result.error:
        print(f"❌ ERROR: {result.error}")
        return

    print(f"✓ Endpoints found: {len(result.endpoints)}")
    if result.endpoints:
        print("\n  First 5 endpoints:")
        for ep in result.endpoints[:5]:
            print(f"    {ep['method']} {ep['path']}")

    print(f"✓ Auth methods: {len(result.auth_methods)}")
    if result.auth_methods:
        for auth in result.auth_methods:
            print(f"    - {auth['type']}")

    print(f"✓ Sample URLs: {len(result.sample_urls)}")
    if result.sample_urls:
        for url in result.sample_urls[:3]:
            print(f"    - {url}")

    print(f"✓ Use cases: {len(result.use_cases)}")
    if result.use_cases:
        for uc in result.use_cases[:3]:
            print(f"    - {uc[:60]}...")

    print(f"✓ Code snippets: {len(result.wrapper_hints)}")
    if result.wrapper_hints:
        print(f"    - First snippet: {result.wrapper_hints[0][:80]}...")

    print(f"✓ Raw sections: {len(result.raw_sections)}")
    if result.raw_sections:
        for section_name in list(result.raw_sections.keys())[:3]:
            print(f"    - {section_name}")

    print()


def test_bs4(url, app_name):
    """Test BeautifulSoup scraper."""
    print("\n🔍 Testing BS4Scraper (static HTML)...")
    scraper = BS4Scraper()
    result = scraper.scrape(url, app_name)
    print_result(result)


def test_scrapy(url, app_name):
    """Test Scrapy/multi-page crawler."""
    print("\n🔍 Testing ScrapyScraper (multi-page crawl)...")
    scraper = ScrapyScraper()
    result = scraper.scrape(url, app_name)
    print_result(result)


def test_selenium(url, app_name):
    """Test Selenium scraper."""
    print("\n🔍 Testing SeleniumScraper (JS-rendered)...")
    scraper = SeleniumScraper()
    result = scraper.scrape(url, app_name)
    print_result(result)


def test_octoparse(url, app_name):
    """Test Octoparse scraper."""
    print("\n🔍 Testing OctoparseScraper (complex sites)...")
    scraper = OctoparseScraper()
    result = scraper.scrape(url, app_name)
    print_result(result)


def main():
    print("\n" + "=" * 60)
    print("SmartDevTool — Manual Scraper Tests")
    print("=" * 60)

    # Get user input
    url = input("\n🔗 Enter URL to scrape: ").strip()
    if not url:
        print("❌ URL cannot be empty")
        return

    if not url.startswith("http"):
        url = "https://" + url

    app_name = input("📱 Enter app name (or press Enter to auto-detect): ").strip()
    if not app_name:
        app_name = url.split("//")[1].split("/")[0].split(".")[-2].title()

    print(f"\n✓ URL: {url}")
    print(f"✓ App name: {app_name}")

    print("\n\n" + "=" * 60)
    print("Available scrapers:")
    print("=" * 60)
    print("1. BS4Scraper - BeautifulSoup (static HTML)")
    print("2. ScrapyScraper - Multi-page crawler")
    print("3. SeleniumScraper - JavaScript rendering")
    print("4. OctoparseScraper - Complex/auth sites")
    print("5. Test ALL scrapers")
    print("=" * 60)

    choice = input("\n🎯 Pick a scraper (1-5): ").strip()

    if choice == "1":
        test_bs4(url, app_name)
    elif choice == "2":
        test_scrapy(url, app_name)
    elif choice == "3":
        test_selenium(url, app_name)
    elif choice == "4":
        test_octoparse(url, app_name)
    elif choice == "5":
        print("\n⚙️  Running all scrapers...\n")
        test_bs4(url, app_name)
        test_scrapy(url, app_name)
        test_selenium(url, app_name)
        test_octoparse(url, app_name)
    else:
        print("❌ Invalid choice")
        return

    # Option to save results
    save = input("\n💾 Save results? (y/n): ").strip().lower()
    if save == "y":
        from src.storage import StorageManager
        from src.agent import SmartAgent

        agent = SmartAgent()
        print("\n🤖 Running full SmartAgent pipeline...")
        result, record = agent.run(url, app_name)
        print(f"✓ Saved with ID: {record.id}")
        print(f"✓ File: {record.file_path}")


if __name__ == "__main__":
    main()
