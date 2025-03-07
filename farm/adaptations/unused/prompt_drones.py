from farm.adaptations.unused.prompt_template import SmartFarmPromptTemplate


class DronesLLMTemplate(SmartFarmPromptTemplate):

    def create_prompt(self, simulation):
        prompt = super().create_prompt(simulation)

        prompt += '\nThink step by step. First, reason about the question and write a short explanation of your answer. Then, on a separate line, write "Final answer:". After that, write one line for each drone with the group selected for the drone (in format "Drone_<N>: <group>", the group name must be exactly as listed above).'

        return prompt

    def process_response(self, response, simulation):
        answer = self.extract_answer(response)
        drone_rows = answer.split("\n")

        assigned_drones = []

        for row in drone_rows:
            try:
                if row == "" or row == "```":
                    continue
                row = row.replace("- ", "")  # remove leading hyphens
                row = row.replace("**", "")  # remove bold

                drone_id, group = row.split(":")
                drone = simulation.dronesDict[drone_id.strip()]
                assigned_drones.append(drone)
                if group.strip() == "idle":
                    drone.assignTarget(None)
                elif group.strip() == "charging":
                    drone.assignTarget(simulation.charger)
                elif group.strip().startswith("protecting"):
                    field_id = group.strip().split()[1]
                    field_idx = int(field_id[-1]) - 1
                    drone.assignTarget(simulation.fields[field_idx])
                else:
                    print(f"Unknown group: {group}")
            except (ValueError, KeyError, IndexError) as error:
                print(f"Invalid row ({error}): {repr(row)}")

        total_assignments = len(assigned_drones)
        unique_drones = set(assigned_drones)
        if len(unique_drones) != total_assignments or total_assignments != len(self.available_drones(simulation)):
            print(f"Wrong groups assignment. Unique drones: {len(unique_drones)}, total_assignments: {total_assignments}, available_drones: {len(self.available_drones(simulation))}")


if __name__ == "__main__":
    template = DronesLLMTemplate()
    prompt = template.create_prompt()
    count = template.count_tokens(prompt)
    print(count)
