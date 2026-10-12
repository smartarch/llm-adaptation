from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # All villagers present in the village for this step
        pool = list(components)
        if not pool:
            return

        # Current wheat available in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        idx = 0
        # Spawn Warriors first: 2 villagers + 12 wheat -> 1 Warrior spawned
        while idx + 1 < len(pool) and wheat >= 12:
            environment.assign_group(pool[idx], "spawn warrior")
            environment.assign_group(pool[idx + 1], "spawn warrior")
            idx += 2
            wheat -= 12

        # Then spawn Farmers: 2 villagers + 10 wheat -> 1 Farmer spawned
        while idx + 1 < len(pool) and wheat >= 10:
            environment.assign_group(pool[idx], "spawn farmer")
            environment.assign_group(pool[idx + 1], "spawn farmer")
            idx += 2
            wheat -= 10

        # Remaining villagers: assign based on their role
        for j in range(idx, len(pool)):
            c = pool[j]
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack the Dragon; Farmers return to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")