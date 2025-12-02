import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        n = len(components)
        # Plan: per-index target group to guarantee one assignment per villager
        plan = ["farm"] * n  # default

        # First, assign by role
        farmers_idx = []
        for i, c in enumerate(components):
            role = getattr(c, "role", None)
            if role == "Farmer":
                plan[i] = "farm"
                farmers_idx.append(i)
            elif role == "Warrior":
                plan[i] = "cave"
            else:
                plan[i] = "farm"  # fallback for unknown

        # Attempt to spawn two Farmers if possible
        if len(farmers_idx) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            i1, i2 = farmers_idx[0], farmers_idx[1]
            plan[i1] = "spawn farmer"
            plan[i2] = "spawn farmer"

        # Attempt to spawn two Warriors from the remaining villagers
        spawn_farmer_set = set()
        if len(farmers_idx) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            spawn_farmer_set.update([farmers_idx[0], farmers_idx[1]])

        candidates_for_war = [i for i in range(n) if i not in spawn_farmer_set]
        if len(candidates_for_war) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            w1, w2 = candidates_for_war[0], candidates_for_war[1]
            plan[w1] = "spawn warrior"
            plan[w2] = "spawn warrior"

        # Apply plan: assign each villager exactly once
        for i, c in enumerate(components):
            environment.assign_group(c, plan[i])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack; Farmers go to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "cave")