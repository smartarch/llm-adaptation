from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Improved strategy:
        # - Warriors go to cave (attack) whenever encountered in village context.
        # - Farmers in village:
        #     1) Use wheat to spawn Farmer pairs as soon as possible (needs 2 farmers + 10 wheat per spawn).
        #     2) After farmer-spawns, consider Warrior-spawns if there are at least 2 remaining farmers
        #        and enough wheat for 2 villagers + 12 wheat (per pair).
        #     3) Remaining farmers go to farm (produce more wheat).
        group_for_assign = {group: [] for group in group_ids}

        # Classify villagers in village context
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # If any warriors are in village (defensive fallback), send them to cave
        for w in warriors:
            group_for_assign["cave"].append(w)

        # Wheat available at Farm
        wheat = getattr(environment.farm, "wheat", 0)

        F = len(farmers)

        # Step 1: spawn farmer pairs as long as possible
        pf = min(F // 2, wheat // 10)
        k_farm_spawn = 2 * pf
        wheat -= pf * 10

        # Step 2: with any remaining farmers, consider warrior-spawns if wheat permits
        remaining_after_pf = F - k_farm_spawn
        pw = 0
        if remaining_after_pf >= 2 and wheat >= 12:
            pw = min(remaining_after_pf // 2, wheat // 12)
        k_war_spawn = 2 * pw
        wheat -= pw * 12

        # Step 3: assign farmers to groups
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
        # Strategy: Warriors attack; Farmers stay in cave as a safe fallback (prefer to keep them in cave if they land here)
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