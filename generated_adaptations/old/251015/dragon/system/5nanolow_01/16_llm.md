```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Adaptive strategy (growth-first with limited DPS ramp-up):
        - Warriors in the village context are always redirected to the cave (attack) to maximize DPS from turn 1.
        - Farmers stay in the village and are used to grow the wheat supply.
        - Spawn Farmer pairs aggressively when possible to seed population growth (requires 2 Farmers and 10 wheat per spawn).
        - Warrior spawns are allowed only in earlier steps (to boost early DPS) and only if there is enough wheat
          to cover both the two new villagers and the 12 wheat cost.
        - Strategy variants by step:
            step < 10  -> allow farmer spawns; allow some warrior spawns if wheat permits
            10 <= step < 20 -> constrain warrior spawns more; prioritize farming
            step >= 20 -> minimize or disable warrior spawns to preserve wheat for farming
        - All remaining farmers go to farm to keep wheat production going.
        """
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

        # Determine whether we allow Warrior spawns based on step
        allow_war_spawn = True
        if step is not None:
            if step < 10:
                allow_war_spawn = True
            elif step < 20:
                # moderate constraint
                allow_war_spawn = True
            else:
                # late game: avoid warrior spawns to preserve wheat for farming
                allow_war_spawn = False

        # Spawn Farmer pairs as long as possible
        pf = min(F // 2, wheat // 10)
        k_farm_spawn = 2 * pf
        wheat -= pf * 10

        # Remaining farmers after farmer-spawns
        remaining_after_pf = F - k_farm_spawn

        # Warrior-spawns conditional on step and resources
        k_war_spawn = 0
        if allow_war_spawn and remaining_after_pf >= 2 and wheat >= 12:
            # Cap number of warrior-spawns to keep farming viable
            pw = min(remaining_after_pf // 2, wheat // 12)
            k_war_spawn = 2 * pw
            wheat -= pw * 12

        # Allocate farmers to groups
        if k_farm_spawn > 0:
            for f in farmers[:k_farm_spawn]:
                group_for_assign["spawn farmer"].append(f)

        if k_war_spawn > 0:
            for f in farmers[k_farm_spawn:k_farm_spawn + k_war_spawn]:
                group_for_assign["spawn warrior"].append(f)

        remaining_farmers = farmers[k_farm_spawn + k_war_spawn:]
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
                group_for_assign["cave"].append(c)
            else:
                group_for_assign["cave"].append(c)

        for gid, lst in group_for_assign.items():
            for c in lst:
                environment.assign_group(c, gid)
```