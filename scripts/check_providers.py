from src.config.settings import get_provider_settings
from src.providers.openai import OpenAIProvider
from src.providers.gemini import GeminiBenchmarkProvider
from src.providers.mistral import MistralBenchmarkProvider
from src.providers.nvidia import NvidiaBenchmarkProvider
from src.providers.llm7 import LLM7BenchmarkProvider

def main():
    settings = get_provider_settings()
    print("Provider Settings loaded successfully!")

    try:
        OpenAIProvider(model_id="gpt-5-nano")
        print("OpenAI initialized.")
    except Exception as e:
        print(f"OpenAI error (expected if missing key but shouldn't be os.environ): {e}")

    try:
        GeminiBenchmarkProvider(model_id="gemini-3.1-flash-lite", allow_live=True)
        print("Gemini initialized.")
    except Exception as e:
        print(f"Gemini error: {e}")

    try:
        MistralBenchmarkProvider(model_id="mistral-large-latest", allow_live=True)
        print("Mistral initialized.")
    except Exception as e:
        print(f"Mistral error: {e}")

    try:
        NvidiaBenchmarkProvider(model_id="meta/llama3-70b-instruct", allow_live=True)
        print("Nvidia initialized.")
    except Exception as e:
        print(f"Nvidia error: {e}")

    try:
        LLM7BenchmarkProvider(model_id="gemini/gemini-3.1-flash-lite", allow_live=True)
        print("LLM7 initialized.")
    except Exception as e:
        print(f"LLM7 error: {e}")

if __name__ == "__main__":
    main()
