from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ScrapeResult:
    url: str
    app_name: str
    tool_used: str
    endpoints: list[dict]
    auth_methods: list[dict]
    sample_urls: list[str]
    use_cases: list[str]
    wrapper_hints: list[str]
    raw_sections: dict
    error: str = ""


@dataclass
class AppRecord:
    id: str
    app_name: str
    url: str
    tool_used: str
    file_path: str
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
