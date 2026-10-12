from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Track assignments to ensure each farmer is assigned exactly once
        assigned = {f: None for f in farmers}

        # 1) Spawn a Farmer if possible (needs 2 farmers and >= 10 wheat)
        if len(farmers) >= 2 and wheat >= 10:
            f1, f2 = farmers[0], farmers[1]
            environment.assign_group(f1, "spawn farmer")
            environment.assign_group(f2, "spawn farmer")
            assigned[f1] = "spawn farmer"
            assigned[f2] = "spawn farmer"
            wheat -= 10

        # 2) Spawn a Warrior if possible from remaining unassigned farmers
        remaining = [f for f in farmers if assigned.get(f) is None]
        if len(remaining) >= 2 and wheat >= 12:
            w1, w2 = remaining[0], remaining[1]
            environment.assign_group(w1, "spawn warrior")
            environment.assign_group(w2, "spawn warrior")
            assigned[w1] = "spawn warrior"
            assigned[w2] = "spawn warrior"
            wheat -= 12

        # 3) Assign all other farmers to farming
        for f in farmers:
            if assigned.get(f) is None:
                environment.assign_group(f, "farm")

        # 4) All Warriors go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack; Farmers should return to Village
        for v in components:
            if getattr(v, "role", None) == "Warrior":
                environment.assign_group(v, "attack")
            else:
                environment.assign_group(v, "village")