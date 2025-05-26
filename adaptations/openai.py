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

        reasoning_summary = config.get("adaptation_params", {}).get("reasoning_summary", None)
        if reasoning_summary is not None:
            model_kwargs = {"reasoning": {"summary": reasoning_summary}}
            if reasoning_effort is not None:
                model_kwargs["reasoning"]["effort"] = reasoning_effort
                del kwargs["reasoning_effort"]
            return ChatOpenAI(model=model, use_responses_api=True, model_kwargs=model_kwargs, **kwargs)

        return ChatOpenAI(model=model, max_tokens=None, **kwargs)
