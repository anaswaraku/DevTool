# SmartDevTool

**Intelligent API Documentation Scraper with AI-Powered Tool Selection**

SmartDevTool is an automated system that extracts structured API documentation from diverse reference sites using intelligent multi-strategy scraping. It employs a sophisticated agent that analyzes website structure and dynamically selects the optimal extraction tool for each site, then stores and indexes the results for natural language querying via LLM.

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites-and-dependencies)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [Solution Approach](#solution-approach)

---

## Features

- **Multi-Strategy Extraction** — Static HTML parsing, JavaScript rendering, multi-page crawling, and complex site handling
- **Structured Data Extraction** — Automatically identifies endpoints, authentication methods, examples, and use cases
- **Intelligent Tool Selection** — AI agent analyzes URL structure and HTML content to choose optimal scraper
- **Persistent Storage** — JSON-based document storage with registry system for tracking extracted data
- **Natural Language Querying** — Query extracted documentation using conversational language via Groq LLM
- **Streamlit Web Interface** — User-friendly dark-themed dashboard for scraping and querying
- **CLI Support** — Programmatic access via Python API for automation

---

## Prerequisites and Dependencies

### System Requirements

- **Python 3.10+**
- **Operating System:** Windows, macOS, or Linux
- **RAM:** Minimum 2GB (4GB+ recommended for Selenium operations)
- **Disk Space:** ~500MB for dependencies and storage

### API Keys

- **Groq API Key** — Required for LLM-powered features (free tier available at https://console.groq.com)

### Python Dependencies

All dependencies are listed in `requirements.txt`:

```
duckduckgo-search       # Web search functionality
beautifulsoup4          # Static HTML parsing
lxml                    # XML/HTML processing
chromadb                # Vector storage and retrieval
streamlit               # Web interface framework
python-dotenv           # Environment variable management
requests                # HTTP client
newspaper3k             # Article extraction
groq                    # LLM API client
selenium                # Browser automation
webdriver-manager       # Chrome driver management
```

---

## Setup & Installation

### 1. Clone and Navigate to Project

```bash
cd d:\SmartDevTool
```

### 2. Create Python Virtual Environment

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
echo GROQ_API_KEY=your_groq_api_key_here > .env
```

Get your Groq API key from https://console.groq.com



---

## Usage

### Option 1: Web Interface (Recommended for Most Users)

```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser. Use the sidebar to:

- Enter API documentation URLs to scrape
- View extraction results in structured format
- Query extracted data using natural language
- Download results as JSON

### Option 2: Command Line / Python API

```bash
python tests/test_scrapers_manual.py
```

---

## Solution Approach

### Architecture Overview

The system implements an intelligent **agent-based orchestration pattern** with specialized tools for different scraping scenarios:

### 1. **Smart Tool Selection (Agent)**

- **Input Analysis:** Fetches first 8KB of target URL's HTML to understand site structure
- **LLM Analysis:** Sends URL and HTML snippet to Groq LLM for classification
- **Confidence Check:** Falls back to rule-based tool selection (`can_handle()`) if LLM response is ambiguous
- **Tool Selection Priority:**
  1. **OctoparseScraper** — Paid API for complex/protected sites (95% success, variable speed)
  2. **SeleniumScraper** — Browser automation for JavaScript SPAs (85% success, ~12s)
  3. **ScrapyScraper** — Multi-page crawling for static sites (30% success, ~5s)
  4. **BS4Scraper** — Fast BeautifulSoup parsing for basic HTML (20% success, ~1s)

### 2. **Extraction Tools**

| Tool              | Best For                       | Speed    | Success Rate | Tech Stack           |
| ----------------- | ------------------------------ | -------- | ------------ | -------------------- |
| **BeautifulSoup** | Simple static HTML docs        | ~1s      | ~20%         | HTML parsing         |
| **Scrapy**        | Multi-page crawling, sitemaps  | ~5s      | ~30%         | Distributed crawling |
| **Selenium**      | JavaScript-rendered SPAs       | ~12s     | ~85%         | Headless Chrome      |
| **Octoparse**     | Complex/JavaScript-heavy sites | Variable | ~95%         | Cloud API            |

### 3. **Fallback Cascade**

When the primary tool returns incomplete results:

1. If primary tool errored → Retry with BeautifulSoup
2. If <5 endpoints on docs site → Run Scrapy multi-page crawl
3. If still 0 endpoints → LLM extraction from raw text
4. If still no authentication info → LLM analysis of raw HTML

### 4. **Data Pipeline**

```
URL Input
  ↓
HTML Peek (first 8KB)
  ↓
LLM-Powered Tool Selection
  ↓
Scraper Execution
  ↓
Fallback Cascade (if needed)
  ↓
Structured Data: Endpoints, Auth, Examples
  ↓
Persistent JSON Storage + Registry
  ↓
ChromaDB Indexing for LLM Queries
```

### 5. **Storage & Querying**

- **Storage:** JSON files in `data/` directory with unique app IDs
- **Registry:** Central `registry.json` tracks all extracted APIs
- **Retrieval:** ChromaDB vector database enables semantic search across extracted documentation

### Key Design Decisions

- **LLM as Classifier:** Reduces false positives in tool selection vs. heuristics alone
- **Intelligent Fallbacks:** Graceful degradation when primary tool fails
- **Tool Specialization:** Each tool optimized for specific site patterns (reduces overhead)
- **Persistent Storage:** Extracted data reusable across sessions without re-scraping
