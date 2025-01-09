from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI

from adaptations.llm import LLMAdaptation


class GoogleAIAdaptation(LLMAdaptation):

    @staticmethod
    def create_llm(model="gemini-1.5-flash", config=None):
        print("LLM model:", model)

        # free API has limited requests per minute
        if config is not None \
                and "adaptation_params" in config \
                and "rpm_limit" in config["adaptation_params"]:
            rpm_limit = int(config["adaptation_params"]["rpm_limit"])
        else:
            rpm_limit = 10

        rate_limiter = InMemoryRateLimiter(
            requests_per_second=rpm_limit/60,
            check_every_n_seconds=1,
            max_bucket_size=1,
        )

        return ChatGoogleGenerativeAI(model=model, max_tokens=None, rate_limiter=rate_limiter)
