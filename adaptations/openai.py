from langchain_openai import ChatOpenAI

from adaptations.llm import LLMAdaptation


class OpenAIAdaptation(LLMAdaptation):

    @staticmethod
    def create_llm(model="gpt-4o-mini-2024-07-18"):
        print("LLM model:", model)
        return ChatOpenAI(model=model, max_tokens=None)
