from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Build a final assignment map for this step
        final_group = {}

        # Baseline: Warriors go to the Cave; Farmers stay in Farm
        farmers = []
        for c in components:
            if getattr(c, "role", "") == "Warrior":
                final_group[c] = "cave"
            else:
                final_group[c] = "farm"
                farmers.append(c)

        # Wheat available in the Farm
        remaining_wheat = getattr(environment.farm, "wheat", 0)

        # Ensure at least two Farmers stay in the Farm (baseline production)
        farm_candidates = [c for c in farmers if final_group.get(c) == "farm"]
        reserved_in_farm = farm_candidates[:2] if len(farm_candidates) >= 2 else farm_candidates.copy()
        for c in reserved_in_farm:
            final_group[c] = "farm"  # explicitly keep them in farm

        # Farm candidates eligible for spawning (excluding reserved)
        sp_farm_candidates = [c for c in farm_candidates if c not in reserved_in_farm]

        # Spawn Farmers: need 2 villagers and 10 wheat
        sp_farm_set = set()
        while len(sp_farm_candidates) >= 2 and remaining_wheat >= 10:
            a = sp_farm_candidates.pop(0)
            b = sp_farm_candidates.pop(0)
            final_group[a] = "spawn farmer"
            final_group[b] = "spawn farmer"
            sp_farm_set.update([a, b])
            remaining_wheat -= 10

        # Spawn Warriors: use remaining farm candidates not already spawning as farmers
        sp_war_candidates = [c for c in farm_candidates if c not in sp_farm_set and final_group.get(c) == "farm"]
        sp_war_set = set()
        while len(sp_war_candidates) >= 2 and remaining_wheat >= 12:
            a = sp_war_candidates.pop(0)
            b = sp_war_candidates.pop(0)
            final_group[a] = "spawn warrior"
            final_group[b] = "spawn warrior"
            sp_war_set.update([a, b])
            remaining_wheat -= 12

        # Apply final assignments (each component assigned exactly once)
        for comp, grp in final_group.items():
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack; Farmers retreat to Village
        for comp in components:
            if getattr(comp, "role", "") == "Warrior":
                grp = "attack"
            else:
                grp = "village"
            environment.assign_group(comp, grp)