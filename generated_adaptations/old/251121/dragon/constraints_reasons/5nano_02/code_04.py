import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Build a single, explicit plan: component -> target_group
        plan = {}

        # Classify villagers
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default assignments: Farmers->farm, Warriors->cave
        for c in components:
            role = getattr(c, "role", None)
            if role == "Farmer":
                plan[c] = "farm"
            elif role == "Warrior":
                plan[c] = "cave"
            else:
                # Fallback if role is unknown
                plan[c] = "farm"

        # Attempt to spawn a new Farmer: need 2 villagers in "spawn farmer" and 10 wheat
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            a, b = farmers[0], farmers[1]
            plan[a] = "spawn farmer"
            plan[b] = "spawn farmer"

        # Attempt to spawn a new Warrior: need 2 villagers in "spawn warrior" and 12 wheat
        # Exclude those already allocated to "spawn farmer"
        candidates = [c for c in components if plan.get(c) != "spawn farmer"]
        if len(candidates) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            c1, c2 = candidates[0], candidates[1]
            plan[c1] = "spawn warrior"
            plan[c2] = "spawn warrior"

        # Apply the plan: assign each component exactly once
        for c, target in plan.items():
            environment.assign_group(c, target)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack the Dragon; Farmers go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback for unknown roles
                environment.assign_group(c, "cave")