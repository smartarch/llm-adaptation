Reasoning and updated strategy

New idea to improve win speed:
- We need a robust balance between growing wheat (via Farmers farming) and increasing the Dragon’s DPS by adding Warriors quickly.
- The previous methods either over-spawned (risking wheat) or under-spawned (slower DPS). To improve, I’m introducing a two-phase, wheat-aware spawning strategy with a clear Lookahead:
  - Phase 1 (early steps): Prioritize creating Warriors to boost early damage, but still respect a farming minimum so wheat continues to grow.
  - Phase 2 (later steps): Use a full lookahead to pick the best combination of spawns (spawn Farmer and spawn Warrior) that maximizes total spawns (and favors Warriors when tied), while ensuring enough Farmers remain to keep wheat flowing.
- This approach guarantees:
  - All Warriors go to the Cave (attack path) when in Village step, as required.
  - Farmers stay in Village to farm (and spawn) with a guaranteed farming minimum to avoid wheat starvation.
  - Spawn decisions respect the exact two-villager-per-spawn rule: for every 2 villagers put in a spawn group, plus the required wheat, a new villager is spawned.

Strategy outline:
- In assign_in_village:
  - Collect Farmers (F) and Warriors (Wv) present.
  - Read current Wheat (W) from environment.farm.wheat.
  - Let min_farm be a small hard guard: if F > 0 then min_farm = 1, else 0.
  - Phase decision by step:
    - If step < 6: do a simple early aggression policy: sp_f = 0, sp_w = min((F - min_farm) // 2, W // 12). This quickly increases DPS early, while ensuring at least one Farmer farms if possible.
    - Else (phase 2): run a robust lookahead to choose the best (sp_f, sp_w) by enumerating feasible values given:
      - 2*sp_f + 2*sp_w <= F - min_farm
      - 10*sp_f + 12*sp_w <= W
      - maximize sp_f + sp_w, breaking ties in favor of larger sp_w (more Warriors).
    - After choosing sp_f and sp_w, assign:
      - First farm_count farmers to "farm"
      - Next 2*sp_f farmers to "spawn farmer"
      - Next 2*sp_w farmers to "spawn warrior"
      - Remaining farmers to "farm"
      - All Warriors to "cave" (they will be moved to "attack" in assign_in_cave)
- In assign_in_cave:
  - Keep Warriors in "attack"
  - Keep Farmers in "village" (fallbacks if groups missing)

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

        min_farm = 1 if F > 0 else 0

        # Early phase policy (phase 1): aggressive Warrior spawning but with farming guard
        sp_f = 0
        sp_w = 0
        farm_count = F

        if F == 0:
            # No farmers, just send warriors to cave
            if cave_gid is not None:
                for w in warriors:
                    environment.assign_group(w, cave_gid)
            return

        if step < 6:
            # Early game: focus on Warriors, but keep at least one farmer farming
            if F - min_farm > 0:
                sp_w = min((F - min_farm) // 2, W // 12)
                farm_count = F - 2 * sp_w
                sp_f = 0
                if farm_count < min_farm:
                    farm_count = min_farm
                    sp_w = max(0, (F - farm_count) // 2)
        else:
            # Phase 2: robust lookahead to maximize total spawns
            max_sp_f = min((F - min_farm) // 2, W // 10) if F - min_farm >= 0 else 0
            best_sp_f = 0
            best_sp_w = 0
            best_farm_count = F
            best_score = -1

            for cand_sp_f in range(max_sp_f, -1, -1):
                remaining = F - 2 * cand_sp_f
                max_sp_w = min(remaining // 2, (W - 10 * cand_sp_f) // 12)
                if max_sp_w < 0:
                    continue
                farm_after = F - 2 * cand_sp_f - 2 * max_sp_w
                if farm_after < min_farm:
                    continue
                score = cand_sp_f + max_sp_w
                # Prefer higher total spawns; tie-break toward more Warriors
                if score > best_score or (score == best_score and max_sp_w > best_sp_w):
                    best_score = score
                    best_sp_f = cand_sp_f
                    best_sp_w = max_sp_w
                    best_farm_count = farm_after

            if best_score >= 0:
                sp_f = best_sp_f
                sp_w = best_sp_w
                farm_count = best_farm_count
            else:
                sp_f = 0
                sp_w = 0
                farm_count = F

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
                # Fallbacks
                if village_gid is not None:
                    environment.assign_group(c, village_gid)
                elif cave_gid is not None:
                    environment.assign_group(c, cave_gid)
```