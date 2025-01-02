from langchain_anthropic import ChatAnthropic

from adaptations.llm import LLMAdaptation


class AnthropicAdaptation(LLMAdaptation):

    @staticmethod
    def create_llm(model="claude-3-5-haiku-20241022", config=None):
        print("LLM model:", model)

        return ChatAnthropic(model=model)
