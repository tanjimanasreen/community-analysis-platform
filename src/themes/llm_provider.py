import abc
import json
import requests
from typing import Optional
from openai import OpenAI

class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate_theme(self, text: str) -> dict:
        """
        Takes a string of keywords and returns a dictionary mapping themes to those keywords.
        """
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        
    def generate_theme(self, text: str) -> dict:
        completion = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", 
                 "content": "You are an expert who can find meaningful themes from a list of keywords, that may contain specific events, people, locations, or topics."},
                {"role": "user", 
                 "content": f'Based on the list of the keywords given below, provide only the exact theme and the corresponding keywords in a coherent short sentence in a JSON. The keys of the json should be theme names and values should be corresponding keywords. There could be one theme or multiple themes for each set of keywords. Here is the list of keywords: {text}'
                }
            ],
            seed=42,
            temperature=0,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        
    def generate_theme(self, text: str) -> dict:
        prompt = f"""You are an expert who can find meaningful themes from a list of keywords, that may contain specific events, people, locations, or topics.

Based on the list of the keywords given below, provide only the exact theme and the corresponding keywords in a coherent short sentence in a JSON. The keys of the json should be theme names and values should be corresponding keywords. There could be one theme or multiple themes for each set of keywords.

Here is the list of keywords: {text}

Output strictly valid JSON and nothing else."""

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.0,
                    "seed": 42
                }
            }
        )
        response.raise_for_status()
        result_text = response.json().get("response", "")
        
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            # Fallback if the model wrapped it in markdown code blocks despite format=json
            if "```json" in result_text:
                clean_text = result_text.split("```json")[1].split("```")[0].strip()
                try:
                    return json.loads(clean_text)
                except json.JSONDecodeError:
                    return {"Error": "Failed to parse JSON", "Raw Output": result_text}
            return {"Error": "Failed to parse JSON", "Raw Output": result_text}

class MockProvider(LLMProvider):
    def __init__(self, static_response: dict = None):
        self.static_response = static_response or {"Mock Theme": "mock keyword 1, mock keyword 2"}
        
    def generate_theme(self, text: str) -> dict:
        return self.static_response


class CachedProvider(LLMProvider):
    """In-memory response cache for deterministic theme generation runs."""

    def __init__(self, provider: LLMProvider, cache: Optional[dict] = None):
        self.provider = provider
        self.cache = cache if cache is not None else {}

    def generate_theme(self, text: str) -> dict:
        if text not in self.cache:
            self.cache[text] = self.provider.generate_theme(text)
        return self.cache[text]
