from langchain_openai import ChatOpenAI

from adaptations.llm import LLMAdaptation


class OpenAIAdaptation(LLMAdaptation):

    @staticmethod
    def create_llm(model="gpt-4o-mini-2024-07-18", config=None):
        print("LLM model:", model)
        if config is not None \
                and "adaptation_params" in config \
                and "temperature" in config["adaptation_params"]:
            return ChatOpenAI(model=model, max_tokens=None, temperature=config["adaptation_params"]["temperature"])
        else:
            return ChatOpenAI(model=model, max_tokens=None)
