import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Compute a robust, single-pass plan without overlapping assignments.
        # 1) Identify farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 2) Determine spawn opportunities (single pass, deterministic)
        spawn_farmer_set = set()
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            spawn_farmer_set.update(farmers[:2])

        # 3) Determine potential warriors to spawn (excluding those already assigned to spawn farmer)
        spawn_war_set = set()
        remaining_for_war = [c for c in components if c not in spawn_farmer_set]
        if len(remaining_for_war) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            spawn_war_set.update(remaining_for_war[:2])

        # 4) Apply final plan: assign exactly once per component
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
                    environment.assign_group(c, "farm")  # safe fallback

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