from abc import abstractmethod, ABC
from collections import deque

from langchain_core.messages import HumanMessage, BaseMessage

from base_classes.adaptation import Adaptation
from base_classes.prompt_template import import_prompt_template, ProcessingError
from base_classes.simulation import Simulation
from utils import print_prompt, print_response


class LLMAdaptation(Adaptation, ABC):

    def __init__(self, config: dict, llm: str, prompt_template: str, prompt_template_params: dict, adapt_every=1, message_history=False, max_retries=0, **kwargs):
        super().__init__()
        self.llm = self.create_llm(llm, config)
        self.prompt_template = import_prompt_template(prompt_template, prompt_template_params, config)
        self.adapt_every = adapt_every

        self.message_history = self.prepare_message_history(message_history)
        self.max_retries = max_retries
        self.memory: str | None = None

    @staticmethod
    def prepare_message_history(message_history_config: bool | int):
        if not message_history_config:
            message_history_config = 0
        if isinstance(message_history_config, int):
            return deque(maxlen=message_history_config * 2 + 1)
        if message_history_config:
            return []

    @staticmethod
    @abstractmethod
    def create_llm(model="gpt-4o-mini-2024-07-18", config=None):
        print("LLM model:", model)
        return ...

    def adapt(self, simulation: "Simulation", step: int):
        if (step - 1) % self.adapt_every != 0:
            return

        session = []
        self.message_history.append(session)
        prompt = self.prompt_template.create_prompt(simulation, self.memory)

        for _ in range(self.max_retries + 1):
            session.append(HumanMessage(prompt))
            response = self.prompt_llm()
            session.append(response)

            simulation.reset_assignments()
            errors, memory = self.prompt_template.process_response(response.content, simulation)
            if memory is not None:
                self.memory = memory

            if errors is None or errors == []:  # success
                break

            prompt = self.get_retry_prompt(errors)

    def prompt_llm(self):
        messages: list[BaseMessage] = []
        for session in self.message_history:
            for message in session:
                messages.append(message)

        print_prompt(messages[-1].content)
        response = self.llm.invoke(messages)
        print_response(response.content)

        return response

    @staticmethod
    def get_retry_prompt(errors: list[ProcessingError]):
        prompt = "There were some errors in your final group assignment. Fix them and output the final assignment again. Adhere to the format defined earlier."

        for row, error in errors:
            prompt += "\n\n"
            if row:
                prompt += f'Error on line "{row}":\n'
            prompt += error

        return prompt
