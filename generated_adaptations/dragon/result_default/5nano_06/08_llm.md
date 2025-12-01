Reasoning and updated strategy

Root cause of continued poor results
- The spawning logic previously did not respect the requirement that two villagers must be assigned to a spawn group for each new villager spawned. We effectively used 1 villager per spawned villager, which underutilized wheat and reduced attacker growth.
- Additionally, spawning decisions sometimes starved farming, risking wheat flow and future spawns.

New strategy (robust, wheat-aware, and faster to win)
- For each step in assign_in_village, allocate villagers to:
  - farm: stay in village to farm (produces wheat)
  - spawn farmer: two villagers assigned to this group yield one new Farmer (requires 10 wheat per spawned Farmer)
  - spawn warrior: two villagers assigned to this group yield one new Warrior (requires 12 wheat per spawned Warrior)
- To maximize growth while ensuring wheat production, we:
  - Always preserve at least one Farmer to keep wheat flowing (if any Farmers exist).
  - Enumerate possible spawns (sp_f for Farmers, sp_w for Warriors) under constraints:
    - 2*sp_f + 2*sp_w <= F - min_farm
    - 10*sp_f + 12*sp_w <= W
  - Choose the combination with the most total spawns (sp_f + sp_w), breaking ties towards more Warriors if beneficial for early DPS.
- After deciding spawns, assign:
  - The first farm_count farmers to the "farm" group
  - The next 2*sp_f farmers to "spawn farmer"
  - The next 2*sp_w farmers to "spawn warrior"
  - Any remaining farmers to "farm"
  - All Warriors to the "cave" group (they will attack in the cave step)
- In assign_in_cave, keep Warriors in "attack" and Farmers back in "village" (with a fallback if groups are missing).

This approach ensures:
- Spawn utilization is correct (2 villagers per spawn).
- Wheat flow is maintained through farming.
- Attacker count grows quickly without starving farming.

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
        farm_count = F  # default: all farmers farm

        # Dynamic, wheat-aware spawning with farming guard
        if F >= 2 and W >= 10:
            max_sp_f = (F - min_farm) // 2
            found = False
            # Try to maximize total spawns; explore sp_f from high to low
            for cand_sp_f in range(max_sp_f, -1, -1):
                remaining = F - 2 * cand_sp_f  # farmers left after allocating sp_f pairs
                max_sp_w = remaining // 2
                for cand_sp_w in range(max_sp_w, -1, -1):
                    W_after = W - 10 * cand_sp_f - 12 * cand_sp_w
                    if W_after < 0:
                        continue
                    farm_after = F - 2 * cand_sp_f - 2 * cand_sp_w
                    if farm_after >= min_farm:
                        sp_f = cand_sp_f
                        sp_w = cand_sp_w
                        farm_count = farm_after
                        found = True
                        break
                if found:
                    break
        if not (F >= 2 and W >= 10) or not found:
            sp_f = 0
            sp_w = 0
            farm_count = F

        # Assign deterministically
        idx = 0

        # 1) Farmers to farm (as many as farm_count)
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