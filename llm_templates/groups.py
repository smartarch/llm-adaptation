import textwrap

from base_classes.llm_template import LLMTemplate


class GroupsLLMTemplate(LLMTemplate):

    def create_prompt(self, simulation) -> str:
        return textwrap.dedent(f"""\
            You are a coordinator for a smart farm. Your goal is to manage a fleet of drones to protect the fields on the farm against birds. The overall goal is to minimize the damage to the fields.
            
            Fields on the farm with their location (rectangles) and bird-threat level (0 to 1):
            {"".join(self.field_attributes(field) for field in simulation.fields)}\
            
            Available drones:
            {"".join(self.drone_attributes(drone) for drone in simulation.drones)}\
            
            Your goal is to divide the drones among the following groups:
            1. idle
            2. charging
            3. protecting Field_1
            4. protecting Field_2
            5. protecting Field_3
            
            Think step by step. First, reason about the question and write a short explanation of your answer. Then, on a separate line, write "Final answer:". After that, write one line per group. The line must start with the group number followed by a colon (':') and then a comma-separated list of drones assigned to the group.
            """)

    def process_response(self, response, simulation):
        answer = self.extract_answer(response)
        groups = answer.split("\n")

        for drone in self.extract_drone_list(groups[0], simulation):  # idle
            drone.target = None
        for drone in self.extract_drone_list(groups[1], simulation):  # charging
            drone.target = "Charger"
        for field, group in zip(simulation.fields, groups[2:]):
            for drone in self.extract_drone_list(group, simulation):  # protecting
                drone.target = field

        pass

    @staticmethod
    def extract_drone_list(line, simulation):
        group, drones = line.split(":")
        drone_names = [d.strip() for d in drones.split(",")]
        return [simulation.dronesDict[name] for name in drone_names if name != ""]


if __name__ == "__main__":
    template = GroupsLLMTemplate()
    prompt = template.create_prompt()
    count = template.count_tokens(prompt)
    print(count)
