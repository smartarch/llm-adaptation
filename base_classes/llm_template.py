import abc
import importlib
import textwrap
from typing import TYPE_CHECKING

import tiktoken

from components.drone import Drone, DroneState
from components.field import Field
from utils import case_insensitive_partition

if TYPE_CHECKING:
    from simulation import SmartFarmSimulation


class PromptTemplate(abc.ABC):

    def __init__(self, extra_goal: str, field_attributes: dict, drone_attributes: dict, config: dict):
        self.extra_goal = extra_goal
        self.field_attributes_config = field_attributes
        self.drone_attributes_config = drone_attributes
        self.charging = ("no_charging" not in config or not config["no_charging"])

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
        final_answer = final_answer.rstrip()     # remove trailing empty lines
        return final_answer

    @staticmethod
    def count_tokens(text: str) -> int:
        encoding = tiktoken.encoding_for_model("gpt-4")
        return len(encoding.encode(text))

    def field_attributes(self, field: "Field") -> str:
        attributes = textwrap.dedent(f"""\
            - {field.id}
              - left: {field.left}
              - top: {field.top}
              - right: {field.right}
              - bottom: {field.bottom}
            """)
        if self.field_attributes_config["threat_level"]:
            attributes += f"  - threat level: {field.threat_level():.2f}\n"
        if self.field_attributes_config["protecting_drones"]:
            attributes += f"  - protecting: {len(field.protectingDrones)} drones\n"
        if self.field_attributes_config["necessary_drones_for_full_protection"]:
            attributes += f"  - for full protection: {field.necessary_drones_for_full_protection} drones\n"
        return attributes

    def drone_attributes(self, drone: "Drone") -> str:
        target_field = f" ({drone.target.id})" if isinstance(drone.target, Field) else ""
        attributes = textwrap.dedent(f"""\
            - {drone.id}
              - state: {drone.state}{target_field}
              - location: {drone.location}
            """)
        if self.drone_attributes_config["battery"]:
            attributes += f"  - battery: {drone.battery:.2f}\n"
        if self.drone_attributes_config["energy_to_fly_to_charger"]:
            attributes += f"  - battery necessary to reach charger: {drone.energyToFlyToCharger():.2f}\n"

        return attributes


class BasicPromptTemplate(PromptTemplate, abc.ABC):

    def create_prompt(self, simulation) -> str:
        prompt = "You are a coordinator for a smart farm. Your goal is to manage a fleet of drones to protect the fields on the farm against birds. The overall goal is to minimize the damage to the fields.\n"

        prompt += "\nFields on the farm with their location (rectangles) and bird-threat level (0 to 1):\n"
        for field in simulation.fields:
            prompt += self.field_attributes(field)

        prompt += "\nAvailable drones:\n"
        for drone in self.available_drones(simulation):
            prompt += self.drone_attributes(drone)

        prompt += "\nYour goal is to divide the drones among the following groups:\n"
        groups = self.get_groups(simulation)
        for order, group in enumerate(groups, start=1):
            prompt += f"{order}. {group}\n"

        if self.extra_goal != "":
            prompt += f"\n{self.extra_goal}\n"

        return prompt

    @staticmethod
    def available_drones(simulation):
        return [drone for drone in simulation.drones if drone.state != DroneState.TERMINATED]

    def get_groups(self, simulation):
        groups = ["idle"]
        if self.charging:
            groups.append("charging")
        for field in simulation.fields:
            groups.append(f"protecting {field.id}")
        return groups


def import_prompt_template(template_name: str, template_params: dict, config: dict) -> PromptTemplate:
    assert template_name.startswith("prompt_templates.")

    template_module, template_class = template_name.rsplit(".", 1)
    print(f"Loading prompt template {template_class} from module {template_module}")
    module = importlib.import_module(template_module)
    clazz = getattr(module, template_class)

    return clazz(**template_params, config=config)
