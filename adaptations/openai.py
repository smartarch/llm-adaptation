import abc
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from base_classes.adaptation import Adaptation
from base_classes.llm_template import import_prompt_template
from helpers import print_prompt, print_response
from simulation import SmartFarmSimulation, notTerminatedDrones


class OpenAIAdaptation(Adaptation):

    def __init__(self, config: dict, llm: str, adapt_every: int, prompt_template: str, prompt_template_params: dict, message_history=False):
        self.llm = self.create_llm(llm)
        self.prompt_template = import_prompt_template(prompt_template, prompt_template_params, config)
        self.adapt_every = adapt_every

        self.message_history = [] if message_history else None

    @staticmethod
    def create_llm(model="gpt-4o-mini-2024-07-18"):
        print("LLM model:", model)
        llm = ChatOpenAI(model=model, max_tokens=None)
        return llm

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        if (step - 1) % self.adapt_every != 0:
            return

        if not any(notTerminatedDrones(simulation)):  # no drones to adapt
            return

        prompt = self.prompt_template.create_prompt(simulation)
        print_prompt(prompt)
        if self.message_history is not None:
            self.message_history.append(HumanMessage(prompt))
            response = self.llm.invoke(self.message_history)
            self.message_history.append(response)
        else:
            response = self.llm.invoke(prompt)

        print_response(response.content)
        self.prompt_template.process_response(response.content, simulation)
