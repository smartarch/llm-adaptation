Strategy and plan

- What’s failing
  - The tests report assignment errors in edge cases (notably no_initial_warriors) where some villagers end up unassigned or assigned to a group not present in the current group_ids. We must guarantee that every villager is assigned to exactly one valid group from group_ids, regardless of which groups are provided.
- What I’ll fix
  - Harden the per-step assignment with a robust fallback that always assigns any unassigned villager to a valid group from group_ids.
  - Introduce a helper _default_group that picks a sensible default from the actual group_ids using a priority order. This avoids hard-coding a single default and adapts to different test configurations.
  - Preserve the core strategy: Warriors go to the Cave to attack (if possible); Farmers stay in Village to farm or spawn. Spawning behavior remains driven by wheat and should gracefully degrade when spawn groups aren’t present.
  - Add final safety passes in both assign_in_village and assign_in_cave to guarantee full coverage.

What changes you’ll see
- A new helper _default_group that chooses a valid default from group_ids based on a priority list.
- Both assign_in_village and assign_in_cave now use _default_group for their final safety pass, ensuring every villager is assigned even when some groups are missing.

Code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _choose_group(self, group_ids, preferred_order):
        """
        Pick the first group in preferred_order that exists in group_ids.
        If none exist, return the first available group_ids element, or None.
        """
        for g in preferred_order:
            if g in group_ids:
                return g
        if group_ids:
            return group_ids[0]
        return None

    def _default_group(self, group_ids, prefer_village=True):
        """
        Return a robust default group present in group_ids.
        If prefer_village is True, try village-oriented defaults first.
        Otherwise try cave/attack-oriented defaults first.
        """
        if prefer_village:
            # village-oriented priority
            prefs = ["farm", "spawn farmer", "spawn warrior", "village", "cave", "attack"]
        else:
            # cave/attack-oriented priority
            prefs = ["cave", "attack", "village", "farm", "spawn farmer", "spawn warrior"]
        return self._choose_group(group_ids, prefs)

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

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        assigned = set()

        # 1) Try to send Warriors to cave if available
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
                # fallback to farm if available
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

        # Safety: any unassigned villagers go to a safe default village group
        default_group = self._default_group(group_ids, prefer_village=True)
        for c in components:
            if c not in assigned:
                if default_group:
                    environment.assign_group(c, default_group)
                else:
                    # ultimate fallback to first available
                    environment.assign_group(c, group_ids[0])
                assigned.add(c)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: all Warriors should attack; Farmers should go back to Village
        assigned = set()
        has_attack = "attack" in group_ids
        has_village = "village" in group_ids

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior" and has_attack:
                environment.assign_group(c, "attack")
            else:
                # Use a safe default village-like group if possible
                default_group = self._default_group(group_ids, prefer_village=True)
                if default_group:
                    environment.assign_group(c, default_group)
                else:
                    environment.assign_group(c, group_ids[0])
            assigned.add(c)

        # Safety: any unassigned components go to a safe default
        if group_ids:
            default_cave = self._default_group(group_ids, prefer_village=False)
            for c in components:
                if c not in assigned:
                    if default_cave:
                        environment.assign_group(c, default_cave)
                    else:
                        environment.assign_group(c, group_ids[0])
                    assigned.add(c)
```