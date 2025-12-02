from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Collect farmers without assigning them yet to avoid multiple assignments in one step
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]

        # Move all warriors to the cave
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "cave")

        nf = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        idx = 0
        # Spawn at most one warrior pair per step if possible
        max_warriors_this_step = min(1, nf // 2, wheat // 12)
        for _ in range(max_warriors_this_step * 2):
            if idx < nf:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        wheat -= max_warriors_this_step * 12
        nf_left = nf - idx

        # Spawn at most one farmer pair per step with remaining wheat
        max_farm_spawns_this_step = min(nf_left // 2, wheat // 10)
        for _ in range(max_farm_spawns_this_step * 2):
            if idx < nf:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

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