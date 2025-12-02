```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Aggressive DPS-first approach (favor warrior spawns over farmer spawns):
        # - All Warriors in village go to the cave (attack) to maximize near-term DPS.
        # - In the Village, try to spawn as many Warriors as possible:
        #     Each warrior spawn consumes 2 farmers and 12 wheat.
        # - If wheat remains after warrior spawns, we send remaining farmers to farming.
        # - We avoid farmer-spawns in this version to preserve wheat for more warrior spawns and
        #   thus higher immediate DPS.
        group_for_assign = {group: [] for group in group_ids}

        # Classify villagers in village context
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Move any Warriors in village to cave (attack)
        for w in warriors:
            group_for_assign["cave"].append(w)

        # Wheat available at Farm
        wheat = getattr(environment.farm, "wheat", 0)

        F = len(farmers)
        # Maximum number of warrior spawns we can attempt this turn
        max_war_spawns = min(F // 2, wheat // 12)

        k_war_spawn = 2 * max_war_spawns
        wheat -= max_war_spawns * 12

        # Assign farmer-vindices to warrior-spawn group
        if k_war_spawn > 0:
            for f in farmers[:k_war_spawn]:
                group_for_assign["spawn warrior"].append(f)

        # Remaining farmers (if any) go to farming (farm)
        remaining_farmers = farmers[k_war_spawn:]
        for f in remaining_farmers:
            group_for_assign["farm"].append(f)

        # Fallback: ensure all components are assigned
        assigned = []
        for lst in group_for_assign.values():
            assigned.extend(lst)
        unassigned = [c for c in components if c not in assigned]
        for c in unassigned:
            group_for_assign["farm"].append(c)

        # Apply assignments
        for gid, lst in group_for_assign.items():
            for c in lst:
                environment.assign_group(c, gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors should attack; Farmers stay in cave as a safe fallback if present
        group_for_assign = {group: [] for group in group_ids}

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                group_for_assign["attack"].append(c)
            elif role == "Farmer":
                # Farmers in cave should retreat to village context; send to village group
                group_for_assign["village"].append(c)
            else:
                group_for_assign["cave"].append(c)

        for gid, lst in group_for_assign.items():
            for c in lst:
                environment.assign_group(c, gid)
```