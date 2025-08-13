import os

# Thin abstraction so we can swap providers via config.
from interlinked import AI
from interlinked.core.clients.googleaiclient import GoogleAIClient

# Placeholder: extend to support OpenAI or a mock client if needed.
def ask_llm(provider: str, model_name: str, prompt: str) -> str:
    provider = (provider or "google").lower()
    if provider == "google":
        client = GoogleAIClient(model_name=model_name)
        response = AI.ask(prompt=prompt, client=client)
        # Try a few shapes to extract text
        try:
            return response.response
        except AttributeError:
            try:
                return response[0]
            except Exception:
                return str(response)
    elif provider == "mock":
        return "MOCK RESPONSE: " + prompt[:400]
    else:
        # Future: add OpenAI or other providers here.
        raise ValueError(f"Unsupported provider: {provider}")
