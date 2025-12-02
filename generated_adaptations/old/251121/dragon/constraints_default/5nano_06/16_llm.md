Strategy update

- Problem: The tests report persistent assignment errors in edge cases (notably no_initial_warriors) where some villagers end up unassigned or assigned to a group not present in the current group_ids. We need to guarantee that every villager is assigned to exactly one valid group from group_ids, regardless of which groups are provided.
- Plan:
  - Make assignment fully robust by:
    - Always assigning Warriors somewhere even if the cave group isn’t available: use a sensible default village-related group when needed.
    - Always assigning Farmers somewhere in village step, using a robust fallback if preferred groups aren’t present.
    - Introducing a safe, deterministic helper that picks a valid group from group_ids according to a preferred order.
    - Adding a final safety pass in both assign_in_village and assign_in_cave to assign any remaining unassigned villagers to a valid default group.
  - Keep the core gameplay intent: Warriors go to the Cave to attack (when possible); Farmers stay in Village and manage farming or spawning (when possible). Spawning still maximizes the number of new villagers given wheat.

- What you’ll see in code:
  - A helper _choose_group to pick the best valid group from group_ids.
  - Warrior reassignment in village now falls back to a default village group if “cave” isn’t available.
  - All steps include a final safety pass that assigns any unassigned villagers to a valid default group.
  - Spawning behavior remains, but if spawn groups aren’t present they’re gracefully degraded to farming or the closest default.

Code (Python)

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

        # 1) Try to send Warriors to cave if available; otherwise fallback later
        if "cave" in group_ids:
            for w in warriors:
                environment.assign_group(w, "cave")
                assigned.add(w)
        else:
            # No cave group; assign later via safety/default
            pass

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

        # Assign spawned farmers (or fallback)
        for c in spawn_farmers_list:
            if has_spawn_farm:
                environment.assign_group(c, "spawn farmer")
            else:
                # fallback to an available farming group
                if "farm" in group_ids:
                    environment.assign_group(c, "farm")
                else:
                    environment.assign_group(c, group_ids[0])
            assigned.add(c)

        # Assign remaining farmers to farm (fallback if farm not present)
        for c in remaining_farmers:
            if "farm" in group_ids:
                environment.assign_group(c, "farm")
            else:
                environment.assign_group(c, group_ids[0])
            assigned.add(c)

        # Assign spawned warriors (or fallback)
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
        if group_ids:
            default_village = self._choose_group(group_ids, ["farm","spawn farmer","spawn warrior","village","cave","attack"])
            for c in components:
                if c not in assigned:
                    if default_village:
                        environment.assign_group(c, default_village)
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
                default_village = self._choose_group(group_ids, ["village","farm","spawn farmer","spawn warrior","cave","attack"])
                if default_village:
                    environment.assign_group(c, default_village)
                else:
                    environment.assign_group(c, group_ids[0] if group_ids else None)
            assigned.add(c)

        # Safety: any unassigned components go to a safe default
        if group_ids:
            default_cave = self._choose_group(group_ids, ["village","farm","spawn farmer","spawn warrior","cave","attack"])
            for c in components:
                if c not in assigned:
                    if default_cave:
                        environment.assign_group(c, default_cave)
                    else:
                        environment.assign_group(c, group_ids[0])
                    assigned.add(c)
```