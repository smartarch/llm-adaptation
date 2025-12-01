from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # All villagers in the village are provided in `components`
        pool = list(components)
        if not pool:
            return

        # Current wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        i = 0
        # Spawn Farmer pairs: 2 villagers + 10 wheat
        while i + 1 < len(pool) and wheat >= 10:
            environment.assign_group(pool[i], "spawn farmer")
            environment.assign_group(pool[i + 1], "spawn farmer")
            i += 2
            wheat -= 10

        # Spawn Warrior pairs: 2 villagers + 12 wheat
        while i + 1 < len(pool) and wheat >= 12:
            environment.assign_group(pool[i], "spawn warrior")
            environment.assign_group(pool[i + 1], "spawn warrior")
            i += 2
            wheat -= 12

        # Remaining villagers: Warriors -> cave, Farmers -> farm
        for j in range(i, len(pool)):
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