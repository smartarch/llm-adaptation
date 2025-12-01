from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        farm_gid = "farm"
        spawn_f_gid = "spawn farmer"
        spawn_w_gid = "spawn warrior"
        cave_gid = "cave"

        valid_farm = farm_gid in group_ids
        valid_spawn_f = spawn_f_gid in group_ids
        valid_spawn_w = spawn_w_gid in group_ids
        valid_cave = cave_gid in group_ids

        # Read wheat with robust fallback
        W = 0
        try:
            W = int(getattr(environment.farm, "wheat", 0) or 0)
        except Exception:
            W = 0

        total_f = len(farmers)
        min_farm = 1 if total_f > 0 else 0

        spawns_f = 0
        spawns_w = 0
        farm_count = total_f  # default: all farmers farm unless we spawn

        # Compute spawns in a wheat-aware way with minimum farming preserved
        if W >= 10 and total_f >= 2:
            # Initial optimistic allocation for spawns_f
            spawns_f = min((total_f - min_farm) // 2, W // 10)

            # Iteratively ensure we keep at least min_farm farmers farming after spawns
            while spawns_f > 0:
                remaining_f = total_f - 2 * spawns_f
                W_after = W - spawns_f * 10
                spawns_w_tmp = min(remaining_f // 2, W_after // 12)

                new_farm_count = total_f - 2 * spawns_f - 2 * spawns_w_tmp
                if new_farm_count >= min_farm:
                    spawns_w = spawns_w_tmp
                    farm_count = new_farm_count
                    break
                spawns_f -= 1

        # If wheat is not enough or there aren't enough farmers, revert to farming
        if W < 10 or total_f < 2 or spawns_f == 0:
            spawns_f = 0
            spawns_w = 0
            farm_count = total_f

        # Enforce minimum farming if possible
        if farm_count < min_farm:
            # Try to adjust to satisfy minimum farming
            farm_count = min_farm
            # Recompute spawns_f/spawns_w in a best-effort manner
            spawns_f = 0
            spawns_w = 0
            if total_f - min_farm >= 2:
                spawns_f = min((total_f - min_farm) // 2, max(0, W // 10))
                # Recompute spawns_w with updated spawns_f
                while spawns_f > 0:
                    remaining_f = total_f - 2 * spawns_f
                    W_after = W - spawns_f * 10
                    spawns_w_tmp = min(remaining_f // 2, W_after // 12)
                    if total_f - 2 * spawns_f - 2 * spawns_w_tmp >= min_farm:
                        spawns_w = spawns_w_tmp
                        break
                    spawns_f -= 1

        # Assign groups deterministically
        idx = 0
        # 1) Farmers into farm group
        if valid_farm:
            for i in range(min(farm_count, total_f)):
                environment.assign_group(farmers[i], farm_gid)
            idx = farm_count

        # 2) Spawn farmers
        if valid_spawn_f:
            for i in range(int(spawns_f)):
                if idx < total_f:
                    environment.assign_group(farmers[idx], spawn_f_gid)
                    idx += 1

        # 3) Spawn warriors
        if valid_spawn_w:
            for i in range(int(spawns_w)):
                if idx < total_f:
                    environment.assign_group(farmers[idx], spawn_w_gid)
                    idx += 1

        # 4) Remaining farmers go to farm
        while idx < total_f and valid_farm:
            environment.assign_group(farmers[idx], farm_gid)
            idx += 1

        # Warriors: all go to cave (attack)
        if valid_cave:
            for w in warriors:
                environment.assign_group(w, cave_gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attack_gid = "attack" if "attack" in group_ids else None
        cave_gid = "cave" if "cave" in group_ids else None
        village_gid = "village" if "village" in group_ids else None

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior" and attack_gid is not None:
                environment.assign_group(c, attack_gid)
            elif role == "Farmer" and village_gid is not None:
                environment.assign_group(c, village_gid)
            else:
                # Fallbacks to keep things in sensible places
                if village_gid is not None:
                    environment.assign_group(c, village_gid)
                elif cave_gid is not None:
                    environment.assign_group(c, cave_gid)