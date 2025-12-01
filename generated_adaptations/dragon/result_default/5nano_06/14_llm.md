Reasoning and updated strategy

Root idea
- The bottleneck to winning quickly is creating enough damage per step in the Cave while not starving wheat production in the Village.
- Spawns must follow the exact two-villager-per-spawn rule and consume wheat (10 for Farmer, 12 for Warrior). We must also keep a small farming base to generate wheat for future spawns.
- Previous attempts sometimes starved farming or over-specified spawns. The new approach uses a robust, exact-enumeration spawning policy that:
  - Always preserves a minimal farming base (so wheat keeps growing).
  - Enumerates all feasible spawn configurations (sp_f for Farmer-spawns, sp_w for Warrior-spawns) under the resource constraints:
    - 2*sp_f + 2*sp_w <= F - min_farm
    - 10*sp_f + 12*sp_w <= W
  - Chooses the configuration that maximizes total spawns (sp_f + sp_w) and, in case of ties, prioritizes more Warrior spawns for early DPS.
- Allocation plan:
  - First allocate farm_count farmers to the farm group ( village ).
  - Then allocate 2*sp_f farmers to the spawn farmer group.
  - Then allocate 2*sp_w farmers to the spawn warrior group.
  - Remaining farmers stay in the farm group.
  - All Warriors go to the cave (to be moved to attack in assign_in_cave).
- In assign_in_cave, keep Warriors in the attack group if available, otherwise fall back gracefully. Farmers go back to the village.

This approach ensures correct two-villager spawning, preserves wheat production, and rapidly increases attacker count when possible, while still respecting the 30-step loss condition.

Python code

```py
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
        # Group IDs (use only those that exist)
        farm_gid = "farm" if "farm" in group_ids else None
        cave_gid = "cave" if "cave" in group_ids else None
        spawn_f_gid = "spawn farmer" if "spawn farmer" in group_ids else None
        spawn_w_gid = "spawn warrior" if "spawn warrior" in group_ids else None

        farmers, warriors = self._collect_farmers_and_warriors(components)
        F = len(farmers)
        W = self._read_wheat(environment)

        # Determine a sensible minimum farming baseline
        if F >= 2:
            min_farm = 2
        elif F == 1:
            min_farm = 1
        else:
            min_farm = 0

        # No farmers: move all warriors to cave; nothing else to spawn
        if F == 0:
            if cave_gid is not None:
                for w in warriors:
                    environment.assign_group(w, cave_gid)
            return

        # Compute best spawn configuration via exact enumeration
        best_sp_f = 0
        best_sp_w = 0
        best_farm_count = F

        max_sp_f = min((F - min_farm) // 2, W // 10) if F - min_farm >= 0 else 0

        best_score = -1
        found = False

        for cand_sp_f in range(max_sp_f, -1, -1):
            remaining = F - 2 * cand_sp_f
            max_sp_w = min(remaining // 2, (W - 10 * cand_sp_f) // 12)
            if max_sp_w < 0:
                continue
            for cand_sp_w in range(max_sp_w, -1, -1):
                W_after = W - 10 * cand_sp_f - 12 * cand_sp_w
                if W_after < 0:
                    continue
                farm_after = F - 2 * cand_sp_f - 2 * cand_sp_w
                if farm_after < min_farm:
                    continue
                score = cand_sp_f + cand_sp_w
                if score > best_score or (score == best_score and cand_sp_w > best_sp_w):
                    best_score = score
                    best_sp_f = cand_sp_f
                    best_sp_w = cand_sp_w
                    best_farm_count = farm_after
                    found = True

        if not found:
            best_sp_f = 0
            best_sp_w = 0
            best_farm_count = F

        sp_f = best_sp_f
        sp_w = best_sp_w
        farm_count = best_farm_count

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
                # Fallbacks to keep things in sensible places
                if village_gid is not None:
                    environment.assign_group(c, village_gid)
                elif cave_gid is not None:
                    environment.assign_group(c, cave_gid)
```