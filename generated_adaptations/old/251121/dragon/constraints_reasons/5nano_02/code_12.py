import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Build a robust, single-pass plan keyed by id(component) to ensure exactly one assignment per component
        plan_by_id = {}

        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        # Default assignments based on role
        for c in components:
            role = getattr(c, "role", None)
            if role == "Farmer":
                plan_by_id[id(c)] = "farm"
            elif role == "Warrior":
                plan_by_id[id(c)] = "cave"
            else:
                plan_by_id[id(c)] = "farm"  # safe fallback

        # Spawn farmer if possible: need 2 villagers in spawn farmer and 10 wheat
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            f1, f2 = farmers[0], farmers[1]
            plan_by_id[id(f1)] = "spawn farmer"
            plan_by_id[id(f2)] = "spawn farmer"

        # Spawn warrior if possible: need 2 villagers in spawn warrior and 12 wheat
        # Exclude those already designated for spawn farmer
        candidates = [c for c in components if plan_by_id.get(id(c)) != "spawn farmer"]
        if len(candidates) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            w1, w2 = candidates[0], candidates[1]
            plan_by_id[id(w1)] = "spawn warrior"
            plan_by_id[id(w2)] = "spawn warrior"

        # Apply the plan: assign each component exactly once
        for c in components:
            target = plan_by_id.get(id(c), "farm")
            environment.assign_group(c, target)

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