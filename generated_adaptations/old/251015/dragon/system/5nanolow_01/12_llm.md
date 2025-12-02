```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Adaptive growth strategy with a simple step-based cap on aggressive spawning.
        # Goals:
        # - Keep Warriors in the Cave to attack the Dragon.
        # - In the Village: prefer farming to accumulate wheat, with controlled spawning
        #   of Farmers (spawn farmer) and, if wheat and steps allow, Warriors (spawn warrior).
        # - If we are far from the end (lower step), allow some Warrior spawns; as steps grow
        #   larger, reduce or stop Warrior spawns to avoid stalling growth.
        group_for_assign = {group: [] for group in group_ids}

        # Classify villagers in village context
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # If any Warriors in village unexpectedly, move them to cave
        for w in warriors:
            group_for_assign["cave"].append(w)

        # Wheat available at Farm
        wheat = getattr(environment.farm, "wheat", 0)

        F = len(farmers)

        # Step-based policy: allow Warrior-spawns only in earlier steps
        allow_war_spawn = step is None or step < 15  # None or small step -> allow
        if not allow_war_spawn:
            pw = 0
        else:
            # Spawn as many farmer-pairs as possible first
            pf = min(F // 2, wheat // 10)
            k_farm_spawn = 2 * pf
            wheat -= pf * 10

            # Remaining farmers after farmer-spawns
            remaining_after_pf = F - k_farm_spawn

            # Warrior-spawns conditional on available wheat and enough remaining farmers
            pw = 0
            if remaining_after_pf >= 2 and wheat >= 12:
                # Cap Warrior-spawns to keep a balance between growth and DPS
                pw = min(remaining_after_pf // 2, wheat // 12)
            k_war_spawn = 2 * pw
            wheat -= pw * 12

            # Allocate farmers to groups accordingly
            if k_farm_spawn > 0:
                for f in farmers[:k_farm_spawn]:
                    group_for_assign["spawn farmer"].append(f)

            if k_war_spawn > 0:
                for f in farmers[k_farm_spawn:k_farm_spawn + k_war_spawn]:
                    group_for_assign["spawn warrior"].append(f)

            remaining_farmers = farmers[k_farm_spawn + k_war_spawn:]
            for f in remaining_farmers:
                group_for_assign["farm"].append(f)

        # If we couldn't or shouldn't spawn warriors due to step cap, ensure remaining farmers go to farm
        if step is not None and step >= 15:
            # Move any farmers already not assigned to farm to ensure wheat production
            for c in farmers:
                if c not in sum(group_for_assign.values(), []):
                    group_for_assign["farm"].append(c)

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