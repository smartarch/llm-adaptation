import abc
import importlib
from collections import namedtuple
from typing import TYPE_CHECKING

import tiktoken

from utils import case_insensitive_partition

if TYPE_CHECKING:
    from base_classes.simulation import Simulation


ProcessingError = namedtuple("ProcessingError", ("row", "error"))


class PromptTemplate(abc.ABC):

    @abc.abstractmethod
    def create_prompt(self, simulation: "Simulation") -> str:
        return ""

    @abc.abstractmethod
    def process_response(self, response: str, simulation: "Simulation") -> list[ProcessingError] | None:
        pass

    @staticmethod
    def extract_answer(llm_answer: str, separator="Final answer:") -> str:
        _, _, final_answer = case_insensitive_partition(llm_answer, separator)
        final_answer = final_answer.lstrip("*")  # remove bold text from "**Final answer:** no"
        final_answer = final_answer.lstrip()     # remove newline trailing after "Final answer:"
        final_answer = final_answer.rstrip()     # remove trailing empty lines
        return final_answer

    @staticmethod
    def count_tokens(text: str) -> int:
        encoding = tiktoken.encoding_for_model("gpt-4")
        return len(encoding.encode(text))


def import_prompt_template(template_name: str, template_params: dict, config: dict) -> PromptTemplate:
    # assert template_name.startswith("prompt_templates.")

    template_module, template_class = template_name.rsplit(".", 1)
    print(f"Loading prompt template {template_class} from module {template_module}")
    module = importlib.import_module(template_module)
    clazz = getattr(module, template_class)

    return clazz(**template_params, config=config)
