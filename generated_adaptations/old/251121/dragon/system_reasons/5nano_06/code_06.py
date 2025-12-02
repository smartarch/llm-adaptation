from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all current Warriors to the Cave (they will attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available in Farm (read-only in this interface)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        idx = 0  # index into farmers list for assigning to spawn groups

        # 2) Early aggressive spawning (biased to get DPS early)
        # If we can, spawn a Warrior early (step <= 15)
        if step <= 15 and len(farmers) - idx >= 4 and wheat >= 12:
            for _ in range(2):  # assign two farmers to spawn warrior
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Spawn farmers if wheat allows (up to 2 new farmers via 4 farmers in group)
        if step <= 15 and len(farmers) - idx >= 4 and wheat >= 20:
            for _ in range(4):  # assign four farmers to spawn farmer
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Remaining farmers stay in the village and farm
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: all Warriors attack; Farmers go to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")