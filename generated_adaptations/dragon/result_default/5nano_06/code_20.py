from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _collect_farmers_and_warriors(self, components):
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]
        return farmers, warriors

    def _read_wheat(self, environment):
        W = 0
        if hasattr(environment, "farm") and environment.farm is not None:
            try:
                W = int(getattr(environment.farm, "wheat", 0) or 0)
            except Exception:
                W = 0
        return max(0, W)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group IDs (only use ones that exist)
        farm_gid = "farm" if "farm" in group_ids else None
        cave_gid = "cave" if "cave" in group_ids else None
        spawn_f_gid = "spawn farmer" if "spawn farmer" in group_ids else None
        spawn_w_gid = "spawn warrior" if "spawn warrior" in group_ids else None

        farmers, warriors = self._collect_farmers_and_warriors(components)
        F = len(farmers)
        W = self._read_wheat(environment)

        # Minimum farming baseline
        min_farm = 1 if F > 0 else 0

        # If no farmers, nothing to spawn; move all warriors to cave
        if F == 0:
            if cave_gid is not None:
                for w in warriors:
                    environment.assign_group(w, cave_gid)
            return

        # Greedy policy: Warrior spawns first, then Farmer spawns with remaining resources
        sp_w = 0
        sp_f = 0
        farm_count = F

        # 1) Max possible Warrior spawns given Wheat and Farmers left for spawns
        sp_w = min((F - min_farm) // 2, W // 12)
        # 2) With sp_w decided, compute how many Farmer spawns we can still support
        remaining_f_after_w = F - 2 * sp_w
        wheat_after_w = W - 12 * sp_w
        sp_f = min(remaining_f_after_w // 2, wheat_after_w // 10)

        farm_count = F - 2 * sp_w - 2 * sp_f
        if farm_count < min_farm:
            # If we can't keep the farming baseline, adjust by reducing sp_w first
            while sp_w > 0 and farm_count < min_farm:
                sp_w -= 1
                remaining_f_after_w = F - 2 * sp_w
                wheat_after_w = W - 12 * sp_w
                sp_f = min(remaining_f_after_w // 2, wheat_after_w // 10)
                farm_count = F - 2 * sp_w - 2 * sp_f

        # Ensure non-negative
        sp_w = max(0, sp_w)
        sp_f = max(0, sp_f)
        farm_count = max(0, farm_count)

        # Assign deterministically
        idx = 0

        # 1) Farm as many as farm_count
        if farm_gid is not None:
            for i in range(min(farm_count, F)):
                environment.assign_group(farmers[i], farm_gid)
            idx = min(farm_count, F)

        # 2) Spawn farmers: 2*sp_f farmers to spawn farmer group
        if sp_f > 0 and spawn_f_gid is not None:
            for i in range(2 * sp_f):
                j = idx + i
                if j < F:
                    environment.assign_group(farmers[j], spawn_f_gid)
            idx = min(F, idx + 2 * sp_f)

        # 3) Spawn warriors: 2*sp_w farmers to spawn warrior group
        if sp_w > 0 and spawn_w_gid is not None:
            for i in range(2 * sp_w):
                j = idx + i
                if j < F:
                    environment.assign_group(farmers[j], spawn_w_gid)
            idx = min(F, idx + 2 * sp_w)

        # 4) Remaining farmers go to farm
        for j in range(idx, F):
            if farm_gid is not None:
                environment.assign_group(farmers[j], farm_gid)

        # Warriors go to cave (attack path)
        if cave_gid is not None:
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