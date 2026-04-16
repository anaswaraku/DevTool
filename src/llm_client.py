from groq import Groq
from src.config import API_KEY, LLM_MODEL, LLM_MAX_TOKENS


class LLMClient:
    def __init__(self):
        self.client = Groq(api_key=API_KEY)

    def ask(self, prompt: str, system: str = "") -> str:
        kwargs = {
            "model": LLM_MODEL,
            "max_tokens": LLM_MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def ask_json(self, prompt: str, system: str = "") -> str:
        system_json = (
            system + "\n" if system else ""
        ) + "Respond with valid JSON only. No markdown, no explanation."
        return self.ask(prompt, system=system_json)
