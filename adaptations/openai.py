import abc
from typing import TYPE_CHECKING

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from base_classes.adaptation import Adaptation
from base_classes.llm_template import import_prompt_template
from helpers import print_prompt, print_response

if TYPE_CHECKING:
    from simulation import SmartFarmSimulation


class OpenAIAdaptation(Adaptation):

    def __init__(self, llm: str, adaptation_steps: int, prompt_template: str, prompt_template_params: dict):
        self.llm = self.create_llm(llm)
        self.prompt_template = import_prompt_template(prompt_template, prompt_template_params)
        self.adaptation_steps = adaptation_steps

    @staticmethod
    def create_llm(model="gpt-4o-mini-2024-07-18"):
        print("LLM model:", model)
        llm = ChatOpenAI(model=model, max_tokens=None)
        return llm

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        if step % self.adaptation_steps != 1:
            return

        prompt = self.prompt_template.create_prompt(simulation)
        print_prompt(prompt)
        response = self.llm.invoke(prompt)
        print_response(response.content)
        self.prompt_template.process_response(response.content, simulation)
