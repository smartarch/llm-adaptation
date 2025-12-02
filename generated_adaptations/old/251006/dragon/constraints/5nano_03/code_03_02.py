from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Collect farmers in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]

        # Move all Warriors to the cave
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "cave")

        nf = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        idx = 0
        # Conservative spawning: at most one pair per step
        # Try to spawn one pair of Warriors if possible
        if nf - idx >= 2 and wheat >= 12:
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2
            wheat -= 12

        # If no warrior spawned this step, try to spawn one pair of Farmers
        if idx == 0 and nf - idx >= 2 and wheat >= 10:
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2
            wheat -= 10

        # Remaining farmers stay farming
        for i in range(idx, nf):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: Warriors attack the Dragon; Farmers go back to village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")