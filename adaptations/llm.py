import csv
from abc import abstractmethod, ABC
from collections import deque
import time

from colorama import Fore, Style
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel

from base_classes.adaptation import Adaptation
from base_classes.prompt_template import import_prompt_template, ProcessingError
from base_classes.simulation import Simulation
from utils import print_prompt, print_response


def count_tokens_and_exit(text: str):
    import tiktoken
    encoding = tiktoken.encoding_for_model("gpt-4")
    print("Tokens:", len(encoding.encode(text)))
    exit()


class LLMAdaptation(Adaptation, ABC):

    def __init__(self, config: dict, llm: str, prompt_template: str, prompt_template_params: dict, message_history=False, max_retries=0, **kwargs):
        super().__init__()
        self.llm = self.create_llm(llm, config)
        self.prompt_template = import_prompt_template(prompt_template, prompt_template_params, config)

        self.message_history = self.prepare_message_history(message_history)
        self.max_retries = max_retries
        self.memory: str | None = None

        self.token_usages: list[LLMTokenUsage] = []

        self._csv_file = open(f'{config["log_dir"]}/{config["log_file_name"]}.llm.csv', "w", newline="")
        self.csv_writer = csv.writer(self._csv_file)
        self.csv_writer.writerow(["step", "try", "errors", "input_tokens", "output_tokens", "reasoning_tokens", "response_time"])

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
    def create_llm(model="gpt-4o-mini-2024-07-18", config=None) -> BaseChatModel:
        print("LLM model:", model)
        raise NotImplementedError()

    def adapt(self, simulation: "Simulation", step: int):
        session = []
        self.message_history.append(session)
        prompt = self.prompt_template.create_prompt(simulation, self.memory)

        for retry in range(self.max_retries + 1):
            session.append(HumanMessage(prompt))
            response = self.prompt_llm()
            session.append(response)

            simulation.reset_assignments()
            errors, memory = self.prompt_template.process_response(response.content, simulation, retry > 0)
            if memory is not None:
                self.memory = memory

            self.csv_writer.writerow([step, retry, len(errors) if errors else 0] + self.token_usages[-1].to_csv())

            if errors is None or errors == []:  # success
                break

            prompt = self.get_retry_prompt(errors)

    def prompt_llm(self):
        messages: list[BaseMessage] = []
        for session in self.message_history:
            for message in session:
                messages.append(message)

        print_prompt(messages[-1].content)
        # count_tokens_and_exit(messages[-1].content)
        start_time = time.time()
        response = self.llm.invoke(messages)
        end_time = time.time()
        print_response(response)
        self.token_usages.append(LLMTokenUsage(response, response_time=end_time - start_time))
        self.token_usages[-1].print()

        return response

    def get_retry_prompt(self, errors: list[ProcessingError]):
        retry_format = self.prompt_template.configuration.get("retry_format", None)

        prompt = "There were some errors in your final group assignment. Fix them and output the final assignment again."

        for processing_error in errors:
            prompt += "\n\n"
            if processing_error.row:
                prompt += f'Error on line "{processing_error.row}":\n'
            prompt += processing_error.error.message

        prompt += "\n\n"
        if retry_format is not None:
            if retry_format == "component-first":
                # FIXME: this should be moved to the prompt template
                prompt += 'To fix the errors, output a group assignment for the incorrectly assigned components. This time, use the `<correction>` and `</correction>` tags to mark the answer (instead of `<answer>`). Note that the output format for corrections is different than for the previous answer.\nFor each of the incorrectly assigned components, write one line with the selected group in format "<name>: <group>". Only include the components that were not assigned correctly (they are listed in the errors above).'
            else:
                raise NotImplementedError()
        else:
            prompt += "Fix the errors and output the final group assignment again. Adhere to the format defined earlier."

        return prompt

    def end(self, simulation: "Simulation"):
        total_usage = sum(self.token_usages, LLMTokenUsage(None))
        total_usage.print()
        self._csv_file.close()


class LLMTokenUsage:

    def __init__(self, response: AIMessage | None, input_tokens=0, output_tokens=0, reasoning_tokens=0, response_time=None):
        if response is None or response.usage_metadata is None:
            self.input_tokens = input_tokens
            self.output_tokens = output_tokens
            self.reasoning_tokens = reasoning_tokens
        else:
            self.input_tokens = response.usage_metadata.get('input_tokens', 0)
            self.output_tokens = response.usage_metadata.get('output_tokens', 0)
            self.reasoning_tokens = response.usage_metadata.get('output_token_details', {}).get('reasoning', 0)
        self.response_time = response_time

    def __add__(self, other):
        return LLMTokenUsage(
            None,
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.reasoning_tokens + other.reasoning_tokens,
            (self.response_time or 0) + (other.response_time or 0)
        )

    def print(self):
        print(Fore.YELLOW, end="")
        print("TOKENS USED:")
        print(f"Input: {self.input_tokens}, ", end="")
        print(f"Output: {self.output_tokens} (reasoning: {self.reasoning_tokens})")
        if self.response_time is not None:
            print(f"Response time (seconds): {self.response_time:.1f}")
        print(Style.RESET_ALL)

    def to_csv(self):
        return [self.input_tokens, self.output_tokens, self.reasoning_tokens, self.response_time]
