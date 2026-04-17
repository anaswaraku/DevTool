# SmartDevTool

Automated API documentation scraper that extracts structured information from API reference sites using multiple strategies (BeautifulSoup, Scrapy, Selenium, Octoparse).

## Quick Start

```bash
# Install
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key_here" > .env

# Use
streamlit run app.py              # Web UI
python tests/test_scrapers_manual.py  # CLI
```

## Usage

**Web Interface:**

```bash
streamlit run app.py
```

**Programmatic:**

```python
from src.agent import SmartAgent
from src.query import QueryEngine

agent = SmartAgent()
result, record = agent.run("https://api.example.com/docs", "ExampleAPI")

engine = QueryEngine()
answer = engine.answer(result, "How do I authenticate?")
```

## Features

- Multi-strategy extraction (static HTML, JavaScript rendering, multi-page crawling)
- Structured data: endpoints, authentication, examples, use cases
- JSON-based persistent storage with registry
- Natural language querying via LLM
- Streamlit web interface

## Tool Orchestration

4 extraction tools, each specialized for different documentation types:

- **BS4Scraper** — Fast BeautifulSoup-based parsing for static HTML docs (~1s, ~20% success rate)
- **ScrapyScraper** — Multi-page breadth-first crawling for static sites (~5s, ~30% success rate)
- **SeleniumScraper** — Chrome headless rendering for JavaScript SPAs (~12s, ~85% success rate)
- **OctoparseScraper** — Paid API wrapper for complex/protected sites (variable speed, ~95% success rate)

Orchestration via `SmartAgent` analyzes URL structure and selects optimal tool automatically.

## Requirements

- Python 3.10+
- Groq API key (for LLM features)
