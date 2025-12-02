from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _compute_spawn_counts(self, farmers, wheat_available):
        """
        Return (spawn_farm_count, spawn_war_count) maximizing total spawns
        given:
          - farmers: list of Farmer components in the Village
          - wheat_available: int
        Each spawn of a Farmer requires 2 Farmers and 10 wheat (spawn farmer),
        or 2 Farmers and 12 wheat (spawn warrior).
        """
        N = len(farmers)
        W = int(wheat_available)

        if N < 2 or W < 10:
            return 0, 0

        # Scenario A: spawn farmers first, then warriors
        max_farm_A = min(N // 2, W // 10)
        rem_farm_A = N - 2 * max_farm_A
        rem_wheat_A = W - 10 * max_farm_A
        max_war_A = min(rem_farm_A // 2, rem_wheat_A // 12)
        total_A = max_farm_A + max_war_A

        # Scenario B: spawn warriors first, then farmers
        max_war_B = min(N // 2, W // 12)
        rem_farm_B = N - 2 * max_war_B
        rem_wheat_B = W - 12 * max_war_B
        max_farm_B = min(rem_farm_B // 2, rem_wheat_B // 10)
        total_B = max_war_B + max_farm_B

        if total_A >= total_B:
            return max_farm_A, max_war_A  # (spawn_farm_count, spawn_war_count)
        else:
            return max_farm_B, max_war_B

    def _safe_assign(self, env, comp, group, group_ids, assigned):
        # Only assign if the group is valid; otherwise do nothing here.
        if group in group_ids:
            env.assign_group(comp, group)
            assigned.add(comp)
            return True
        return False

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Collect villagers by role (unknown roles may appear; handled in fallback)
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        assigned = set()

        # 1) All Warriors go to the Cave (if allowed)
        if "cave" in group_ids:
            for w in warriors:
                environment.assign_group(w, "cave")
                assigned.add(w)

        # 2) Spawning strategy for Farmers (maximize spawns given wheat)
        wheat_available = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            try:
                wheat_available = int(environment.farm.wheat)
            except Exception:
                wheat_available = 0

        spawn_farm_cnt, spawn_war_cnt = self._compute_spawn_counts(farmers, wheat_available)

        # Respect group_id availability for spawning groups
        has_spawn_farm = "spawn farmer" in group_ids
        has_spawn_war = "spawn warrior" in group_ids

        if not has_spawn_farm:
            spawn_farm_cnt = 0
        if not has_spawn_war:
            spawn_war_cnt = 0

        # Allocate farmers to spawn groups and farming
        spawn_farmers_list = farmers[:2 * spawn_farm_cnt]
        rest_after_farm = farmers[2 * spawn_farm_cnt:]
        spawn_warrior_list = rest_after_farm[:2 * spawn_war_cnt]
        remaining_farmers = rest_after_farm[2 * spawn_war_cnt:]

        for c in spawn_farmers_list:
            if has_spawn_farm:
                environment.assign_group(c, "spawn farmer")
            else:
                # fallback to farm or default
                if "farm" in group_ids:
                    environment.assign_group(c, "farm")
                else:
                    environment.assign_group(c, group_ids[0])
            assigned.add(c)

        for c in remaining_farmers:
            if "farm" in group_ids:
                environment.assign_group(c, "farm")
            else:
                environment.assign_group(c, group_ids[0])
            assigned.add(c)

        for c in spawn_warrior_list:
            if has_spawn_war:
                environment.assign_group(c, "spawn warrior")
            else:
                if "farm" in group_ids:
                    environment.assign_group(c, "farm")
                else:
                    environment.assign_group(c, group_ids[0])
            assigned.add(c)

        # Safety: any unassigned farmers go to safe default (prefer farm)
        if farmers:
            default_village = "farm" if "farm" in group_ids else group_ids[0]
            for c in farmers:
                if c not in assigned:
                    environment.assign_group(c, default_village)
                    assigned.add(c)

        # Note: Warriors were already assigned when possible; or defaulted above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: all Warriors should attack; Farmers should go back to Village
        assigned = set()
        has_attack = "attack" in group_ids
        has_village = "village" in group_ids
        default_cave = "village" if has_village else (group_ids[0] if group_ids else None)

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior" and has_attack:
                environment.assign_group(c, "attack")
            else:
                if has_village:
                    environment.assign_group(c, "village")
                elif group_ids:
                    environment.assign_group(c, group_ids[0])
                else:
                    # last resort (shouldn't happen in valid tests)
                    environment.assign_group(c, None)  # may raise; but tests ensure valid ids
            assigned.add(c)

        # Safety: any unassigned components go to a safe default
        if components:
            default_group = default_cave if 'default_cave' in locals() else (group_ids[0] if group_ids else None)
            for c in components:
                if c not in assigned:
                    if default_group and default_group in group_ids:
                        environment.assign_group(c, default_group)
                    elif group_ids:
                        environment.assign_group(c, group_ids[0])
                    else:
                        environment.assign_group(c, None)
                    assigned.add(c)