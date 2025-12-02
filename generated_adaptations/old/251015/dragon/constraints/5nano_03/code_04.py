import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate current villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Policy: all Warriors go to the Cave (attack later), Farmers stay in Village
        for w in warriors:
            environment.assign_group(w, "cave")

        F = len(farmers)
        if F == 0:
            return

        # Wheat available in the Farm (may be zero)
        wheat = getattr(environment.farm, "wheat", 0)
        if wheat < 0:
            wheat = 0

        # Plan spawns: maximize warriors first, then farmers
        y = min(F // 2, wheat // 12)  # number of Warrior-spawns
        wheat_after_warrior_spawns = wheat - 12 * y
        F_remaining_after_warrior_spawns = F - 2 * y

        x = min(F_remaining_after_warrior_spawns // 2, wheat_after_warrior_spawns // 10)  # number of Farmer-spawns

        # Create an assignment plan for farmers
        assign_list = []
        assign_list.extend(["spawn warrior"] * (2 * y))
        assign_list.extend(["spawn farmer"] * (2 * x))
        remaining = F - len(assign_list)
        assign_list.extend(["farm"] * remaining)

        # If there are still farmers without a group (edge cases), default to farming
        if len(assign_list) < F:
            assign_list.extend(["farm"] * (F - len(assign_list)))

        # Assign groups to farmers in their list order
        for farmer, g in zip(farmers, assign_list):
            environment.assign_group(farmer, g)

        # Warriors were already assigned to "cave" above

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, make Warriors attack and move Farmers back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")