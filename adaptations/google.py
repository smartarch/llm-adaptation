from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI

from adaptations.llm import LLMAdaptation


class GoogleAIAdaptation(LLMAdaptation):

    @staticmethod
    def create_llm(model="gemini-1.5-flash"):
        print("LLM model:", model)

        rate_limiter = InMemoryRateLimiter(
            requests_per_second=15/60,  # free API allows 15 requests per minute for "Gemini 1.5 Flash"
            check_every_n_seconds=1,
            max_bucket_size=1,
        )

        return ChatGoogleGenerativeAI(model=model, max_tokens=None, rate_limiter=rate_limiter)
