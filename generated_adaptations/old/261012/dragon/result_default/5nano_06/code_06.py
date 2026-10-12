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
        if hasattr(environment, "farm"):
            try:
                W = int(getattr(environment.farm, "wheat", 0) or 0)
            except Exception:
                W = 0
        return W

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group IDs
        farm_gid = "farm" if "farm" in group_ids else None
        cave_gid = "cave" if "cave" in group_ids else None
        spawn_f_gid = "spawn farmer" if "spawn farmer" in group_ids else None
        spawn_w_gid = "spawn warrior" if "spawn warrior" in group_ids else None

        farmers, warriors = self._collect_farmers_and_warriors(components)
        F = len(farmers)
        W = self._read_wheat(environment)

        min_farm = 1 if F > 0 else 0

        sp_f = 0
        sp_w = 0
        farm_count = F

        # Dynamic, wheat-aware spawning with farming guard
        if F >= 2 and W >= 10:
            max_sp_f = min(F // 2, W // 10)
            found = False
            for cand_sp_f in range(max_sp_f, -1, -1):
                W_after = W - cand_sp_f * 10
                remaining_f = F - 2 * cand_sp_f
                cand_sp_w = min(remaining_f // 2, W_after // 12)
                farm_after = F - 2 * cand_sp_f - 2 * cand_sp_w
                if farm_after >= min_farm:
                    sp_f = cand_sp_f
                    sp_w = cand_sp_w
                    farm_count = farm_after
                    found = True
                    break
            if not found:
                sp_f = 0
                sp_w = 0
                farm_count = F
        else:
            sp_f = 0
            sp_w = 0
            farm_count = F

        # Fallback: ensure minimum farming if possible
        if farm_count < min_farm:
            farm_count = min_farm
            sp_f = 0
            sp_w = 0
            # Try a best-effort adjustment if there is room
            if F - min_farm >= 2:
                max_sp_f = min((F - min_farm) // 2, W // 10)
                for cand_sp_f in range(max_sp_f, -1, -1):
                    W_after = W - cand_sp_f * 10
                    remaining_f = F - 2 * cand_sp_f - min_farm
                    cand_sp_w = min(remaining_f // 2, W_after // 12)
                    if min_farm + 2 * cand_sp_f + 2 * cand_sp_w <= F:
                        sp_f = cand_sp_f
                        sp_w = cand_sp_w
                        farm_count = F - 2 * sp_f - 2 * sp_w
                        break

        # Assign deterministically
        idx = 0

        # 1) Farmers to farm (as many as farm_count)
        if farm_gid is not None:
            for i in range(min(farm_count, len(farmers))):
                environment.assign_group(farmers[i], farm_gid)
            idx = min(farm_count, len(farmers))

        # 2) Spawn farmers
        if spawn_f_gid is not None:
            for i in range(int(sp_f)):
                j = idx + i
                if j < len(farmers):
                    environment.assign_group(farmers[j], spawn_f_gid)
            idx = min(len(farmers), idx + int(sp_f))

        # 3) Spawn warriors
        if spawn_w_gid is not None:
            for i in range(int(sp_w)):
                j = idx + i
                if j < len(farmers):
                    environment.assign_group(farmers[j], spawn_w_gid)
            idx = min(len(farmers), idx + int(sp_w))

        # 4) Remaining farmers go to farm
        for i in range(idx, len(farmers)):
            if farm_gid is not None:
                environment.assign_group(farmers[i], farm_gid)

        # Warriors go to cave (attack)
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
                # Fallbacks
                if village_gid is not None:
                    environment.assign_group(c, village_gid)
                elif cave_gid is not None:
                    environment.assign_group(c, cave_gid)