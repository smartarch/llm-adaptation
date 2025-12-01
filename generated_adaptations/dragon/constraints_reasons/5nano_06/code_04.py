import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Build a non-overlapping plan for this step
        plan = {}

        # 1) All Warriors should go to the Cave (plan = "cave")
        for c in warriors:
            plan[c] = "cave"

        # 2) All Farmers default to "farm"
        for c in farmers:
            plan[c] = "farm"

        # Current wheat in the farm
        current_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # 3) Spawn logic: move some farmers to spawn groups if resources allow
        # Identify farmers currently planned to farm
        farmers_to_seed_farm = [c for c in farmers if plan.get(c) == "farm"]

        # Attempt to spawn a Farmer: need 2 farmers + wheat >= 10
        if len(farmers_to_seed_farm) >= 2 and current_wheat >= 10:
            to_spawn_farmers = farmers_to_seed_farm[:2]
            for c in to_spawn_farmers:
                plan[c] = "spawn farmer"

        # After possible farmer spawn, try to spawn a Warrior with remaining farmers
        remaining_for_warrior = [c for c in farmers if plan.get(c) == "farm"]
        if len(remaining_for_warrior) >= 2 and current_wheat >= 12:
            to_spawn_warriors = remaining_for_warrior[:2]
            for c in to_spawn_warriors:
                plan[c] = "spawn warrior"

        # 4) Apply the plan: assign each component to exactly one group
        for comp, grp in plan.items():
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack; Farmers should go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: keep them in cave if role is unknown
                environment.assign_group(c, "cave")