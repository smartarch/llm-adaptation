from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Build a final assignment map for this step
        final_group = {}

        # Base rule: Warriors go to cave (to attack), Farmers stay in farm
        for c in components:
            if getattr(c, "role", "") == "Warrior":
                final_group[c] = "cave"
            else:
                final_group[c] = "farm"

        # Wheat currently available in the Farm
        remaining_wheat = getattr(environment.farm, "wheat", 0)

        # Lists for convenience
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]

        # Farmers currently in Farm (eligible for spawning a farmer)
        farm_candidates = [c for c in farmers if final_group.get(c) == "farm"]

        # Spawn Farmers: need two villagers and 10 wheat
        sp_farm_candidates = list(farm_candidates)
        while len(sp_farm_candidates) >= 2 and remaining_wheat >= 10:
            a = sp_farm_candidates.pop(0)
            b = sp_farm_candidates.pop(0)
            final_group[a] = "spawn farmer"
            final_group[b] = "spawn farmer"
            remaining_wheat -= 10

        # Spawn Warriors: use remaining farmers not already spawning as farmers
        sp_war_candidates = [c for c in farmers if final_group.get(c) == "farm"]
        # Exclude those already allocated to spawn farmer
        sp_farmed = {c for c, g in final_group.items() if g == "spawn farmer"}
        sp_war_candidates = [c for c in sp_war_candidates if c not in sp_farmed]

        while len(sp_war_candidates) >= 2 and remaining_wheat >= 12:
            a = sp_war_candidates.pop(0)
            b = sp_war_candidates.pop(0)
            final_group[a] = "spawn warrior"
            final_group[b] = "spawn warrior"
            remaining_wheat -= 12

        # Apply final assignments (each component assigned exactly once)
        for comp, grp in final_group.items():
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for comp in components:
            if getattr(comp, "role", "") == "Warrior":
                grp = "attack"
            else:
                grp = "village"
            environment.assign_group(comp, grp)