from langchain_openai import ChatOpenAI

from adaptations.llm import LLMAdaptation


class OpenAIAdaptation(LLMAdaptation):

    @staticmethod
    def create_llm(model="gpt-4o-mini-2024-07-18", config=None):
        print("LLM model:", model)

        kwargs = {}

        temperature = config.get("adaptation_params", {}).get("temperature", None)
        if temperature is not None:
            kwargs["temperature"] = temperature
        reasoning_effort = config.get("adaptation_params", {}).get("reasoning_effort", None)
        if reasoning_effort is not None:
            kwargs["reasoning_effort"] = reasoning_effort

        return ChatOpenAI(model=model, max_tokens=None, **kwargs)
