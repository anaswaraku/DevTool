"""
query.py — QueryEngine: answers natural-language questions about a saved app
           by building a compact context block and calling the LLM.
"""

from src.config import CHUNK_SIZE, MAX_SOURCES
from src.llm_client import LLMClient


SYSTEM_PROMPT = """You are an expert API documentation assistant.
Answer the user's question using ONLY the API documentation context provided below.
Be concise but complete. Use bullet points or code blocks where helpful.
If the answer is not in the context, say "I couldn't find that in the scraped documentation."
Never make up endpoints, parameters or auth details that are not in the context."""


class QueryEngine:

    def __init__(self):
        self.llm = LLMClient()

    # ── Public API ────────────────────────────────────────────────────

    def answer(self, app_data: dict, question: str) -> str:
        """
        Given a loaded app_data dict and a natural-language question,
        return an LLM-generated answer grounded in the scraped content.
        """
        context = self._build_context(app_data)
        prompt = (
            f"=== API DOCUMENTATION CONTEXT ===\n{context}\n\n"
            f"=== USER QUESTION ===\n{question}"
        )
        return self.llm.ask(prompt, system=SYSTEM_PROMPT)

    def summarise(self, app_data: dict) -> str:
        """Generate a one-paragraph executive summary of the scraped API."""
        context = self._build_context(app_data)
        prompt = (
            f"=== API DOCUMENTATION CONTEXT ===\n{context}\n\n"
            f"Write a concise 3–5 sentence summary of what this API does, "
            f"its main endpoints, and how authentication works."
        )
        return self.llm.ask(prompt, system=SYSTEM_PROMPT)

    # ── Private helpers ───────────────────────────────────────────────

    def _build_context(self, app_data: dict) -> str:
        parts: list[str] = []

        # App metadata
        parts.append(f"App: {app_data.get('app_name', 'Unknown')}")
        parts.append(f"URL: {app_data.get('url', '')}")
        parts.append(f"Tool: {app_data.get('tool_used', '')}")
        parts.append("")

        # Endpoints
        endpoints = app_data.get("endpoints", [])
        if endpoints:
            parts.append("## Endpoints")
            for ep in endpoints[:30]:
                method = ep.get("method", "")
                path = ep.get("path", "")
                desc = ep.get("description", "")
                line = f"  {method} {path}"
                if desc:
                    line += f" — {desc}"
                parts.append(line)
            parts.append("")

        # Auth methods
        auth = app_data.get("auth_methods", [])
        if auth:
            parts.append("## Authentication")
            for a in auth:
                atype = a.get("type", "")
                adesc = a.get("description", "")
                parts.append(f"  - {atype}: {adesc}")
            parts.append("")

        # Sample URLs
        samples = app_data.get("sample_urls", [])
        if samples:
            parts.append("## Sample URLs")
            for s in samples[:8]:
                parts.append(f"  {s}")
            parts.append("")

        # Use cases
        use_cases = app_data.get("use_cases", [])
        if use_cases:
            parts.append("## Use Cases")
            for uc in use_cases[:6]:
                parts.append(f"  - {uc}")
            parts.append("")

        # Code snippets / wrapper hints
        hints = app_data.get("wrapper_hints", [])
        if hints:
            parts.append("## Code Snippets")
            for h in hints[:4]:
                parts.append(f"```\n{h[:400]}\n```")
            parts.append("")

        # Raw sections (most information-dense part)
        sections = app_data.get("raw_sections", {})
        if sections:
            parts.append("## Documentation Sections")
            count = 0
            for title, content in sections.items():
                if count >= MAX_SOURCES:
                    break
                if not content or not title:
                    continue
                parts.append(f"### {title}")
                parts.append(content[:CHUNK_SIZE])
                parts.append("")
                count += 1

        return "\n".join(parts)
