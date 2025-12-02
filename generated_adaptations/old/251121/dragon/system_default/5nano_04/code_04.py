from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Decide final one-time group for each component in the village
        final_group = {}

        # Initial simple rule: Warriors stay in village to be moved to cave, Farmers stay farming
        for c in components:
            if getattr(c, "role", "") == "Warrior":
                final_group[c] = "cave"
            else:
                final_group[c] = "farm"

        # Wheat available for spawning
        remaining_wheat = getattr(environment.farm, "wheat", 0)

        # List of farmers
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]

        # Farmers currently in Farm
        farmers_in_farm = [c for c in farmers if final_group.get(c) == "farm"]

        # Spawn Farmer: need 2 villagers in this group and 10 wheat
        sp_farm_candidates = list(farmers_in_farm)
        while len(sp_farm_candidates) >= 2 and remaining_wheat >= 10:
            a = sp_farm_candidates.pop(0)
            b = sp_farm_candidates.pop(0)
            final_group[a] = "spawn farmer"
            final_group[b] = "spawn farmer"
            remaining_wheat -= 10

        # Spawn Warrior: use farmers (not already spawning farmer) and need 2 villagers and 12 wheat
        sp_war_candidates = [c for c in farmers if final_group.get(c) in ("farm", "spawn farmer")]
        while len(sp_war_candidates) >= 2 and remaining_wheat >= 12:
            a = sp_war_candidates.pop(0)
            b = sp_war_candidates.pop(0)
            final_group[a] = "spawn warrior"
            final_group[b] = "spawn warrior"
            remaining_wheat -= 12

        # Apply final group assignments (each component assigned exactly once)
        for comp, grp in final_group.items():
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for comp in components:
            if getattr(comp, "role", "") == "Warrior":
                grp = "attack"
            else:
                grp = "village"
            environment.assign_group(comp, grp)