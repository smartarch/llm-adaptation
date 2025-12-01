Reasoning and updated strategy

Problem recap:
- We want to kill the Dragon as fast as possible. Warriors should end up in the Cave to attack; Farmers stay in the Village to farm and to spawn new villagers when possible.
- Spawning rules: For every two villagers assigned to a spawn group and the required wheat (10 for Farmer-spawn, 12 for Warrior-spawn), a new villager is spawned.
- Wheat must be produced by Farmers who stay in the Village.

Root cause of previous failures:
- Spawning decisions were too aggressive or not consistently preserving a minimum farming base, risking wheat production and the ability to spawn later.
- Some edge cases (no farmers, insufficient wheat, missing groups) could lead to suboptimal allocations or no spawning at all.

What this new approach changes
- A robust, deterministic, wheat-aware spawning policy:
  - Always preserve at least min_farm farmers in farming (min_farm = min(2, F) if possible, otherwise F or 1 if any exist) to keep wheat flowing.
  - Enumerate all feasible spawn configurations (sp_f, sp_w) under:
    - 2*sp_f + 2*sp_w <= F - min_farm
    - 10*sp_f + 12*sp_w <= W
  - Choose the configuration that maximizes total spawns (sp_f + sp_w). If ties, prefer more Warriors (higher DPS early).
- Allocation plan:
  - First assign farm_count farmers to "farm".
  - Then assign 2*sp_f farmers to "spawn farmer".
  - Then assign 2*sp_w farmers to "spawn warrior".
  - Remaining farmers go to "farm".
  - All Warriors go to "cave" (and will be moved to "attack" in assign_in_cave).
- In assign_in_cave, keep Warriors in "attack" and Farmers in "village" (fallbacks if groups are missing).

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
        # Safely read wheat from farm, with fallbacks if the attribute isn't present
        W = 0
        if hasattr(environment, "farm") and environment.farm is not None:
            try:
                W = int(getattr(environment.farm, "wheat", 0) or 0)
            except Exception:
                W = 0
        return max(0, W)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group IDs (only use those available)
        farm_gid = "farm" if "farm" in group_ids else None
        cave_gid = "cave" if "cave" in group_ids else None
        spawn_f_gid = "spawn farmer" if "spawn farmer" in group_ids else None
        spawn_w_gid = "spawn warrior" if "spawn warrior" in group_ids else None

        farmers, warriors = self._collect_farmers_and_warriors(components)
        F = len(farmers)
        W = self._read_wheat(environment)

        # Minimum farming: try to keep at least 2 farmers farming if possible, otherwise 1 if any exist
        min_farm = min(2, F) if F >= 2 else (2 if F >= 1 else 0)

        # If there are no farmers, just assign everyone appropriately
        if F == 0:
            if cave_gid is not None:
                for w in warriors:
                    environment.assign_group(w, cave_gid)
            return

        # Enumerate all feasible spawn configurations
        best_sp_f = 0
        best_sp_w = 0
        best_farm_count = F  # default: all farmers farm
        max_possible_sp_f = min((F - min_farm) // 2, W // 10) if F - min_farm >= 0 else 0

        found = False
        for cand_sp_f in range(max_possible_sp_f, -1, -1):
            remaining_after_sp_f = F - 2 * cand_sp_f
            max_sp_w = remaining_after_sp_f // 2
            for cand_sp_w in range(max_sp_w, -1, -1):
                W_after = W - 10 * cand_sp_f - 12 * cand_sp_w
                if W_after < 0:
                    continue
                farm_after = F - 2 * cand_sp_f - 2 * cand_sp_w
                if farm_after >= min_farm:
                    best_sp_f = cand_sp_f
                    best_sp_w = cand_sp_w
                    best_farm_count = farm_after
                    best_sp_f, best_sp_w = cand_sp_f, cand_sp_w
                    found = True
                    break
            if found:
                break

        if not found:
            best_sp_f, best_sp_w = 0, 0
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

        # 2) Spawn farmers: allocate 2*sp_f farmers to the spawn farmer group
        if sp_f > 0 and spawn_f_gid is not None:
            for i in range(2 * sp_f):
                j = idx + i
                if j < F:
                    environment.assign_group(farmers[j], spawn_f_gid)
            idx = min(F, idx + 2 * sp_f)

        # 3) Spawn warriors: allocate 2*sp_w farmers to the spawn warrior group
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