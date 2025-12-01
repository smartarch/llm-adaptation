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
        # Group IDs (use only the ones that exist)
        farm_gid = "farm" if "farm" in group_ids else None
        cave_gid = "cave" if "cave" in group_ids else None
        spawn_f_gid = "spawn farmer" if "spawn farmer" in group_ids else None
        spawn_w_gid = "spawn warrior" if "spawn warrior" in group_ids else None

        farmers, warriors = self._collect_farmers_and_warriors(components)
        F = len(farmers)
        W = self._read_wheat(environment)

        # If there are no farmers, nothing to spawn; move Warriors to cave
        if F == 0:
            if cave_gid is not None:
                for w in warriors:
                    environment.assign_group(w, cave_gid)
            return

        # Determine minimum farming baseline
        min_farm = min(2, F)  # try to keep up to 2 farming if possible

        # Enumerate all feasible spawn configurations
        best_sp_f = 0
        best_sp_w = 0
        best_farm_after = F
        best_score = -1  # total spawns

        max_sp_f_possible = min((F - min_farm) // 2, W // 10) if F - min_farm >= 0 else 0

        for sp_f in range(0, max_sp_f_possible + 1):
            remaining = F - 2 * sp_f
            max_sp_w_possible = min(remaining // 2, (W - 10 * sp_f) // 12)
            if max_sp_w_possible < 0:
                continue
            for sp_w in range(0, max_sp_w_possible + 1):
                W_after = W - 10 * sp_f - 12 * sp_w
                farm_after = F - 2 * sp_f - 2 * sp_w
                if W_after < 0:
                    continue
                if farm_after < min_farm:
                    continue
                score = sp_f + sp_w
                if score > best_score or (score == best_score and sp_w > best_sp_w):
                    best_score = score
                    best_sp_f = sp_f
                    best_sp_w = sp_w
                    best_farm_after = farm_after

        sp_f = best_sp_f
        sp_w = best_sp_w
        farm_count = best_farm_after

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