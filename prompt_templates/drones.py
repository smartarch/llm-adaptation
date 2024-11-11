import textwrap
from typing import TYPE_CHECKING

from base_classes.llm_template import PromptTemplate
from components.drone import Drone, DroneState


class DronesLLMTemplate(PromptTemplate):

    def create_prompt(self, simulation) -> str:
        return textwrap.dedent(f"""\
            You are a coordinator for a smart farm. Your goal is to manage a fleet of drones to protect the fields on the farm against birds. The overall goal is to minimize the damage to the fields.
            
            Fields on the farm with their location (rectangles) and bird-threat level (0 to 1):
            {"".join(self.field_attributes(field) for field in simulation.fields)}\
            
            Available drones:
            {"".join(self.drone_attributes(drone) for drone in simulation.drones if drone.state != DroneState.TERMINATED)}\
            
            Your goal is to divide the drones among the following groups:
            1. idle
            2. charging
            3. protecting Field_1
            4. protecting Field_2
            5. protecting Field_3
            
            {self.extra_goal}
            
            Think step by step. First, reason about the question and write a short explanation of your answer. Then, on a separate line, write "Final answer:". After that, write one line for each drone with the group selected for the drone (in format "Drone_<N>: <group>", the group name must be exactly as listed above).
            """)

    def process_response(self, response, simulation):
        answer = self.extract_answer(response)
        drone_rows = answer.split("\n")

        for row in drone_rows:
            try:
                drone_id, group = row.split(":")
                drone = simulation.dronesDict[drone_id.strip()]
                if group.strip() in ["idle", "1"]:  # idle
                    drone.assignTarget(None)
                elif group.strip() in ["charging", "2"]:  # charging
                    drone.assignTarget(simulation.charger)
                elif group.strip().startswith("protecting"):  # protecting
                    field_id = group.strip().split()[1]
                    field_idx = int(field_id[-1]) - 1
                    drone.assignTarget(simulation.fields[field_idx])
                else:
                    print(f"Unknown group: {group}")
            except ValueError as error:
                print(f"Invalid row ({error}): {repr(row)}")

    @staticmethod
    def extract_drone_list(line, simulation) -> "list[Drone]":
        group, drones = line.split(":")
        drone_names = [d.strip() for d in drones.split(",")]
        return [simulation.dronesDict[name] for name in drone_names if name in simulation.dronesDict]


if __name__ == "__main__":
    template = DronesLLMTemplate()
    prompt = template.create_prompt()
    count = template.count_tokens(prompt)
    print(count)
