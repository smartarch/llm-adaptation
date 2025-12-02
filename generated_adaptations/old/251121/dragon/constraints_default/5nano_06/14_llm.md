Strategy and plan

- What’s failing
  - The unit tests report assignment errors, meaning some villagers end up unassigned (or ambiguously assigned) during a step, especially when edge-case group_ids are used (e.g., no_initial_warriors). Even though the high-level strategy is preserved (warriors go to cave to attack; farmers stay in village to farm or spawn), edge cases cause some components to escape a concrete group assignment.

- What I’ll fix
  - Harden the per-step assignment to guarantee every component is assigned to exactly one valid group from the provided group_ids.
  - Use robust fallbacks that strictly depend on the actual group_ids present, not on hard-coded group names. If a preferred group is not present, we fall back to the first available group in group_ids.
  - Maintain the spawning behavior (maximize spawns given wheat) but gracefully degrade when a specific spawn group is missing.
  - Add a final safety pass that assigns any still-unassigned villagers to a sensible default group from the current group_ids.

- How this helps the tests
  - No matter what group_ids are provided, every component will be assigned to some valid group, eliminating assignment errors. The spawning behavior remains in place, so functional tests still observe spawning of warriors when possible.

- What changes you’ll see
  - A more defensive approach: after explicit assignments, any leftover component is assigned to a default group that is guaranteed to exist in the current group_ids. The default is chosen to respect the spirit of the task: farmers farm or spawn if possible; warriors go to cave to attack; nothing is left unassigned.

Code (Python)

```py
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

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        assigned = set()

        # 1) All Warriors go to the Cave if possible
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

        # Assign spawned farmers (or fallback)
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

        # Safety: any unassigned villagers (including unknown roles) go to a safe default
        if group_ids:
            default_village = "farm" if "farm" in group_ids else group_ids[0]
            for c in components:
                if c not in assigned:
                    environment.assign_group(c, default_village)
                    assigned.add(c)

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
                    environment.assign_group(c, None)
            assigned.add(c)

        # Safety: any unassigned components go to a safe default
        for c in components:
            if c not in assigned:
                if default_cave and default_cave in group_ids:
                    environment.assign_group(c, default_cave)
                elif group_ids:
                    environment.assign_group(c, group_ids[0])
                else:
                    environment.assign_group(c, None)
                assigned.add(c)
```