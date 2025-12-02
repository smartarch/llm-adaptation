Strategy rationale and changes

- Objective refinement: Ensure we always assign every villager to exactly one group, with Warriors going to the Cave to attack, Farmers staying in the Village to farm or to spawn new villagers. We also want to aggressively spawn new Warriors when wheat allows, to increase combat power early.

- Key improvements:
  1) Robust assignment guarantees:
     - Track assigned villagers in each step and, as a safety net, assign any unassigned villagers to a sensible default (Farm in Village; Village in Cave). This fixes potential assignment errors when some edge-case mix of roles appears.
  2) Optimized spawning distribution:
     - Instead of greedily choosing the spawn type (Farm vs Warrior) in a fixed order, compute the distribution that maximizes total number of spawns given:
       - Each spawn of a Farmer requires 2 Farmers and 10 wheat.
       - Each spawn of a Warrior requires 2 Farmers and 12 wheat.
     - Evaluate two scenarios: Farmer-spawns-first vs Warrior-spawns-first and pick the one yielding more total spawns. This tends to produce more Warriors early when wheat permits, addressing tests that require several Warriors to be spawned soon.
  3) Safe, explicit re-assignment:
     - Always re-assign every component to a group in each step (even if the action would be the same as before). The implementation uses explicit tracking to avoid any component being left unassigned.

- Implementation outline:
  - In assign_in_village:
    - Move all Warriors to cave.
    - For Farmers, compute the best spawn distribution via a small helper that evaluates two scenarios and returns (spawn_farm_count, spawn_war_count).
    - Assign the first 2*spawn_farm_count Farmers to "spawn farmer", the next 2*spawn_war_count Farmers to "spawn warrior", and the remaining Farmers to "farm".
    - As safety, assign any unassigned Farmers to "farm".
  - In assign_in_cave:
    - Warriors -> "attack"; Farmers -> "village".
    - Safety fallback to assign any unassigned components to "village".

- This should fix assignment errors observed in tests and increase the likelihood of spawning Warriors early, improving performance against the Dragon.

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
        Each Farmer spawn consumes 2 farmers and 10 wheat (spawn farmer),
        or 2 farmers and 12 wheat (spawn warrior).
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
        # Collect villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Track assigned components to ensure full coverage
        assigned = set()

        # 1) All Warriors go to the Cave
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

        # Allocate farmers to spawn groups and farming
        spawn_farmers_list = farmers[:2 * spawn_farm_cnt]
        rest_after_farm = farmers[2 * spawn_farm_cnt:]
        spawn_warrior_list = rest_after_farm[:2 * spawn_war_cnt]
        remaining_farmers = rest_after_farm[2 * spawn_war_cnt:]

        for c in spawn_farmers_list:
            environment.assign_group(c, "spawn farmer")
            assigned.add(c)
        for c in remaining_farmers:
            environment.assign_group(c, "farm")
            assigned.add(c)
        for c in spawn_warrior_list:
            environment.assign_group(c, "spawn warrior")
            assigned.add(c)

        # Safety: any unassigned farmers go to farm
        for c in farmers:
            if c not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(c)

        # Note: Warriors already assigned; if there were zero farmers, nothing else to do here.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: all Warriors should attack; Farmers should go back to Village
        assigned = set()
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers and any others go to Village
                environment.assign_group(c, "village")
            assigned.add(c)

        # Safety: any unassigned components (if any) go to Village
        for c in components:
            if c not in assigned:
                environment.assign_group(c, "village")
                assigned.add(c)
```