from generated_adaptations.base_classes dragon import DragonHuntAdaptation
# Note: The import path may vary slightly depending on the project structure.
# The base class is expected to be available at the specified module path.

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Move all Warriors to the cave
        warriors = []
        farmers = []
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "cave")
                warriors.append(c)
            elif role == "Farmer":
                farmers.append(c)
            else:
                # Fallback: keep unknown roles in farm if any
                environment.assign_group(c, "farm")

        # Spawn planning using available wheat
        nf = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        idx = 0

        # Attempt to spawn one farmer if possible (needs 2 villagers and 10 wheat)
        if nf - idx >= 2 and wheat >= 10:
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2

        # Attempt to spawn one warrior if possible (needs 2 villagers and 12 wheat)
        if nf - idx >= 2 and wheat >= 12:
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        # Remaining farmers go to farming
        for i in range(idx, nf):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, assign Warriors to attack; Farmers go back to village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")