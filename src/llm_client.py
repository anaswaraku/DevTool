from groq import Groq
from src.config import GROQ_API_KEY, LLM_MODEL, LLM_MAX_TOKENS


class LLMClient:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def ask(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            messages=messages,
        )
        return response.choices[0].message.content

    def ask_json(self, prompt: str, system: str = "") -> str:
        system_json = (
            system + "\n" if system else ""
        ) + "Respond with valid JSON only. No markdown, no explanation."
        return self.ask(prompt, system=system_json)
