import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Identify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Determine spawning opportunities deterministically
        spawn_farmer_set = set()
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            spawn_farmer_set.update([farmers[0], farmers[1]])

        spawn_war_set = set()
        # Exclude those already chosen for spawning a farmer
        candidates_for_war = [c for c in components if c not in spawn_farmer_set]
        if len(candidates_for_war) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            w1, w2 = candidates_for_war[0], candidates_for_war[1]
            spawn_war_set.update([w1, w2])

        # Assign each component exactly once according to the plan
        for c in components:
            if c in spawn_farmer_set:
                environment.assign_group(c, "spawn farmer")
            elif c in spawn_war_set:
                environment.assign_group(c, "spawn warrior")
            else:
                role = getattr(c, "role", None)
                if role == "Farmer":
                    environment.assign_group(c, "farm")
                elif role == "Warrior":
                    environment.assign_group(c, "cave")
                else:
                    # Fallback for unknown roles
                    environment.assign_group(c, "farm")

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