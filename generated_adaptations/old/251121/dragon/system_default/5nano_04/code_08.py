# Improved adaptation strategy:
# - Adhere to the core rule: all Warriors go to the Cave and attack the Dragon.
#   Farmers stay in the Village to Farm and to spawn new villagers when wheat allows.
# - Spawn logic is made more robust to avoid starving the Farm:
#   - Always keep at least two Farmers assigned to the Farm (to guarantee baseline wheat production).
#   - First, use available Wheat to spawn as many Farmers as possible from the Farm pool.
#   - Then, from the remaining Farm villagers, spawn Warriors as resources allow.
# - This approach aims to accelerate population growth and thus DPS on the Dragon
#   while ensuring the Wheat production never drops to zero for too long.
# - All components are assigned exactly once per step, and the implementation avoids
#   re-assigning the same component multiple times in a single step.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Build a deterministic final assignment map for this step
        final_group = {}

        # Partition roles: Warriors -> cave, Farmers -> farm (baseline)
        farmers = []
        for c in components:
            if getattr(c, "role", "") == "Warrior":
                final_group[c] = "cave"
            else:
                final_group[c] = "farm"
                farmers.append(c)

        # Wheat available in the Farm
        remaining_wheat = getattr(environment.farm, "wheat", 0)

        # Guarantee at least two farmers stay in the Farm (baseline wheat production)
        reserved_in_farm = []
        if len(farmers) >= 2:
            reserved_in_farm = farmers[:2]
            for c in reserved_in_farm:
                final_group[c] = "farm"  # explicitly keep them in farm

        # Farm candidates eligible for spawning (excluding reserved)
        farm_candidates = [c for c in farmers if c not in reserved_in_farm]

        # Spawn Farmers: need 2 villagers and 10 wheat
        sp_farm_candidates = list(farm_candidates)
        sp_farm_set = set()
        while len(sp_farm_candidates) >= 2 and remaining_wheat >= 10:
            a = sp_farm_candidates.pop(0)
            b = sp_farm_candidates.pop(0)
            final_group[a] = "spawn farmer"
            final_group[b] = "spawn farmer"
            sp_farm_set.update([a, b])
            remaining_wheat -= 10

        # Spawn Warriors: use remaining farm candidates not already spawning as farmers
        sp_war_candidates = [c for c in farm_candidates if c not in sp_farm_set]
        sp_war_set = set()
        while len(sp_war_candidates) >= 2 and remaining_wheat >= 12:
            a = sp_war_candidates.pop(0)
            b = sp_war_candidates.pop(0)
            final_group[a] = "spawn warrior"
            final_group[b] = "spawn warrior"
            sp_war_set.update([a, b])
            remaining_wheat -= 12

        # Apply final assignments: ensure every component is assigned exactly once
        for comp, grp in final_group.items():
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack the Dragon; Farmers retreat to the Village
        for comp in components:
            if getattr(comp, "role", "") == "Warrior":
                grp = "attack"
            else:
                grp = "village"
            environment.assign_group(comp, grp)