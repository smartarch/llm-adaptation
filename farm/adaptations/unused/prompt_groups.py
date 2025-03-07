from farm.adaptations.unused.prompt_template import SmartFarmPromptTemplate
from farm.components.drone import Drone


class GroupsLLMTemplate(SmartFarmPromptTemplate):

    def create_prompt(self, simulation):
        prompt = super().create_prompt(simulation)

        prompt += "\nThink step by step. First, reason about the question and write a short explanation of your answer. Then, on a separate line, write \"Final answer:\". After that, write one line per group. The line must start with the group number followed by a colon (':') and then a comma-separated list of drones assigned to the group. If you want to keep a drone assigned to the same group, include it in your answer as well."

        return prompt

    def process_response(self, response, simulation):
        answer = self.extract_answer(response)
        groups = answer.split("\n")

        if not self.charging:
            groups.insert(1, "charging:")  # add empty charging group

        idle = self.extract_drone_list(groups[0], simulation)
        charging = self.extract_drone_list(groups[1], simulation)
        protecting = [self.extract_drone_list(group, simulation) for group in groups[2:]]

        total_assignments = len(idle) + len(charging) + sum(len(group) for group in protecting)
        unique_drones = set.union(set(idle), set(charging), *(set(group) for group in protecting))
        if len(unique_drones) != total_assignments or total_assignments != len(self.available_drones(simulation)):
            print(f"Wrong groups assignment. Unique drones: {len(unique_drones)}, total_assignments: {total_assignments}, available_drones: {len(self.available_drones(simulation))}")

        for drone in idle:
            drone.assignTarget(None)
        for drone in charging:
            drone.assignTarget(simulation.charger)
        for field, group in zip(simulation.fields, protecting):
            for drone in group:
                drone.assignTarget(field)

    @staticmethod
    def extract_drone_list(line, simulation) -> "list[Drone]":
        try:
            group, drones = line.split(":")
            drone_names = [d.strip() for d in drones.split(",")]
            return [simulation.dronesDict[name] for name in drone_names if name in simulation.dronesDict]
        except (ValueError, KeyError, IndexError) as error:
            print(f"Invalid row ({error}): {repr(line)}")
            return []


if __name__ == "__main__":
    template = GroupsLLMTemplate()
    prompt = template.create_prompt()
    count = template.count_tokens(prompt)
    print(count)
