import textwrap
from typing import TYPE_CHECKING

from base_classes.llm_template import PromptTemplate, BasicPromptTemplate
from components.drone import Drone, DroneState


class GroupsLLMTemplate(BasicPromptTemplate):

    def create_prompt(self, simulation):
        prompt = super().create_prompt(simulation)

        prompt += "\nThink step by step. First, reason about the question and write a short explanation of your answer. Then, on a separate line, write \"Final answer:\". After that, write one line per group. The line must start with the group number followed by a colon (':') and then a comma-separated list of drones assigned to the group."

        return prompt

    def process_response(self, response, simulation):
        answer = self.extract_answer(response)
        groups = answer.split("\n")

        # TODO: improve error handling
        if not self.charging:
            groups.insert(1, "charging:")  # add empty charging group
        for drone in self.extract_drone_list(groups[0], simulation):  # idle
            drone.assignTarget(None)
        for drone in self.extract_drone_list(groups[1], simulation):  # charging
            drone.assignTarget(simulation.charger)
        for field, group in zip(simulation.fields, groups[2:]):
            for drone in self.extract_drone_list(group, simulation):  # protecting
                drone.assignTarget(field)

    @staticmethod
    def extract_drone_list(line, simulation) -> "list[Drone]":
        group, drones = line.split(":")
        drone_names = [d.strip() for d in drones.split(",")]
        return [simulation.dronesDict[name] for name in drone_names if name in simulation.dronesDict]


if __name__ == "__main__":
    template = GroupsLLMTemplate()
    prompt = template.create_prompt()
    count = template.count_tokens(prompt)
    print(count)
