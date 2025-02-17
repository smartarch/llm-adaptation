from abc import abstractmethod, ABC
from collections import deque

from langchain_core.messages import HumanMessage

from base_classes.adaptation import Adaptation
from base_classes.prompt_template import import_prompt_template
from utils import print_prompt, print_response
from farm.simulation import SmartFarmSimulation


class LLMAdaptation(Adaptation, ABC):

    def __init__(self, config: dict, llm: str, adapt_every: int, prompt_template: str, prompt_template_params: dict,
                 message_history=False, **kwargs):
        super().__init__()
        self.llm = self.create_llm(llm, config)
        self.prompt_template = import_prompt_template(prompt_template, prompt_template_params, config)
        self.adapt_every = adapt_every

        self.message_history = self.prepare_message_history(message_history)

    @staticmethod
    def prepare_message_history(message_history_config: bool | int):
        if isinstance(message_history_config, int):
            return deque(maxlen=message_history_config * 2 + 1)
        if message_history_config:
            return []
        return None

    @staticmethod
    @abstractmethod
    def create_llm(model="gpt-4o-mini-2024-07-18", config=None):
        print("LLM model:", model)
        return ...

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        if (step - 1) % self.adapt_every != 0:
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
