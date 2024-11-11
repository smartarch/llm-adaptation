import abc
import importlib
from typing import TYPE_CHECKING

import tiktoken

from components.drone import Drone
from components.field import Field
from utils import case_insensitive_partition

if TYPE_CHECKING:
    from simulation import SmartFarmSimulation


class PromptTemplate(abc.ABC):

    @abc.abstractmethod
    def create_prompt(self, simulation: "SmartFarmSimulation") -> str:
        return ""

    @abc.abstractmethod
    def process_response(self, response: str, simulation: "SmartFarmSimulation"):
        pass

    @staticmethod
    def extract_answer(llm_answer: str) -> str:
        _, _, final_answer = case_insensitive_partition(llm_answer, "Final answer:")
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
              - threat level: {field.threat_level():.2f}
              - protecting: {len(field.protectingDrones)} drones
              - for full protection: {field.necessary_drones_for_full_protection} drones
            """

    @staticmethod
    def drone_attributes(drone: "Drone") -> str:
        target_field = f" ({drone.target.id})" if isinstance(drone.target, Field) else ""
        return f"""- {drone.id}
              - state: {drone.state}{target_field}
              - battery: {drone.battery:.2f}
              - location: {drone.location}
              - battery necessary to reach charger: {drone.energyToFlyToCharger():.2f}
            """


def import_prompt_template(template_name: str, template_params: dict) -> PromptTemplate:
    assert template_name.startswith("prompt_templates.")

    template_module, template_class = template_name.rsplit(".", 1)
    print(f"Loading prompt template {template_class} from module {template_module}")
    module = importlib.import_module(template_module)
    clazz = getattr(module, template_class)

    return clazz(**template_params)
