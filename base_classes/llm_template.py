import abc
import textwrap
from typing import TYPE_CHECKING

import tiktoken

from components.drone import Drone

if TYPE_CHECKING:
    from simulation import SmartFarmSimulation
    from components.field import Field


class LLMTemplate(abc.ABC):
    pass

    @abc.abstractmethod
    def create_prompt(self, simulation: "SmartFarmSimulation") -> str:
        return ""

    @abc.abstractmethod
    def process_response(self, response: str, simulation: "SmartFarmSimulation"):
        pass

    @staticmethod
    def extract_answer(llm_answer: str) -> str:
        _, _, final_answer = llm_answer.partition("Final answer:")
        final_answer = final_answer.lstrip("*")  # remove bold text from "**Final answer:** no"
        final_answer = final_answer.lstrip()     # remove newline trailing after "Final answer:"
        return final_answer

    @staticmethod
    def count_tokens(text: str) -> int:
        encoding = tiktoken.encoding_for_model("gpt-4")
        return len(encoding.encode(text))

    @staticmethod
    def field_attributes(field: "Field") -> str:
        return f"""- {field.id}
              - left: {field.left}
              - top: {field.top}
              - right: {field.right}
              - bottom: {field.bottom}
              - threat_level: {field.threat_level():.2f}
            """

    @staticmethod
    def drone_attributes(drone: "Drone") -> str:
        return f"""- {drone.id}
              - state: {drone.state}
              - battery: {drone.battery:.2f}
              - location: {drone.location}
            """
