from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divides villagers in the Village into:
        - "farm": stay in the Village and farm
        - "cave": go to the Cave
        - "spawn farmer": for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - "spawn warrior": for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)

        # Default assignments
        assignments = {}
        for f in farmers:
            assignments[f] = "farm"     # Farmers stay in Village
        for w in warriors:
            assignments[w] = "cave"     # Warriors go to Cave

        # Wheat available for spawning
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Determine how many to spawn (maximize total spawns f + w)
        fspawn = 0
        wspawn = 0
        if F >= 2 and wheat >= 10:
            max_pairs = F // 2  # 2f + 2w <= F  ->  f + w <= F/2
            best_sum = -1
            best_pair = (0, 0)
            # Try all feasible f, w pairs
            for f in range(0, max_pairs + 1):
                # Remaining pairs for w after choosing f
                max_w_by_f = max_pairs - f
                # Wheat constraint: 10f + 12w <= wheat  ->  w <= (wheat - 10f) // 12
                if wheat - 10 * f < 0:
                    continue
                w_max_by_wheat = (wheat - 10 * f) // 12
                w = min(max_w_by_f, w_max_by_wheat)
                if f + w > best_sum:
                    best_sum = f + w
                    best_pair = (f, w)
            fspawn, wspawn = best_pair

        # Assign exact villagers to spawn groups if any
        if fspawn > 0 or wspawn > 0:
            # Ensure we have enough farmers to allocate to spawn groups
            farmers_sorted = farmers  # preserve given order for determinism
            idx = 0

            # First, assign 2*fspawn farmers to "spawn farmer"
            for _ in range(2 * fspawn):
                if idx >= len(farmers_sorted):
                    break
                c = farmers_sorted[idx]
                assignments[c] = "spawn farmer"
                idx += 1

            # Then, assign 2*wspawn farmers to "spawn warrior"
            for _ in range(2 * wspawn):
                if idx >= len(farmers_sorted):
                    break
                c = farmers_sorted[idx]
                # If this farmer was already assigned to spawn farmer, skip (defensive)
                assignments[c] = "spawn warrior"
                idx += 1

        # Apply all assignments
        for c, g in assignments.items():
            environment.assign_group(c, g)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divides villagers in the Cave into:
        - "attack": Attack the Dragon (all Warriors)
        - "cave": Stay in the Cave (if any non-Warriors end up here)
        - "village": Go to the Village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")