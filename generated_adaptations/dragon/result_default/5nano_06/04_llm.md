Reasoning and updated strategy

Root cause of the poor result
- The prior approach tried to maximize spawning but didn’t robustly enforce a minimum farming presence to keep wheat flowing. If wheat runs low or the distribution of farmers to spawn groups deprives farming too much, wheat production stagnates and spawning stalls, delaying the growth of your force.
- All Warriors must go to the Cave to attack, but spawning should be aggressive enough to flood the Cave with attackers quickly while still retaining a single farmer to sustain wheat production for later spawns.

Key improvements
- Dynamic, wheat-aware spawning with a hard minimum of farming to guarantee continued wheat production.
- Ensure at least one farmer remains in farming (if any farmers exist) to keep wheat flowing across steps.
- Aggressive but safe splitting: maximize spawns given current wheat, then fill the rest with farming, while keeping the farmer-minimum constraint satisfied.
- Maintain the rule that all Warriors go to the Cave (via the Cave step) and all Farmers stay in Village for farming/spawning.

Adaptation strategy (high level)
- assign_in_village
  - Partition Farmers into three groups: farm, spawn farmer, spawn warrior; keep at least one farmer farming if possible.
  - Compute spawn numbers using current wheat (W) and number of Farmers (N):
    - If W >= 10 and N >= 2, compute spawns_f (spawn farmers) as many as possible but leave room to keep at least 1 farmer farming.
    - Recompute spawns_w (spawn warriors) based on remaining farmers and remaining wheat, ensuring the total farmers used for spawning does not drop below the minimum farming requirement.
    - Remaining farmers go to farming.
  - All Warriors are assigned to the Cave (to attack) when in village.
- assign_in_cave
  - Warriors go to attack; Farmers go to village. Fall back gracefully if groups are missing.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        farm_gid = "farm"
        spawn_f_gid = "spawn farmer"
        spawn_w_gid = "spawn warrior"
        cave_gid = "cave"

        valid_farm = farm_gid in group_ids
        valid_spawn_f = spawn_f_gid in group_ids
        valid_spawn_w = spawn_w_gid in group_ids
        valid_cave = cave_gid in group_ids

        # Read wheat with robust fallback
        W = 0
        try:
            W = int(getattr(environment.farm, "wheat", 0) or 0)
        except Exception:
            W = 0

        total_f = len(farmers)
        min_farm = 1 if total_f > 0 else 0

        spawns_f = 0
        spawns_w = 0
        farm_count = total_f  # default: all farmers farm unless we spawn

        # Compute spawns in a wheat-aware way with minimum farming preserved
        if W >= 10 and total_f >= 2:
            # Initial optimistic allocation for spawns_f
            spawns_f = min((total_f - min_farm) // 2, W // 10)

            # Iteratively ensure we keep at least min_farm farmers farming after spawns
            while spawns_f > 0:
                remaining_f = total_f - 2 * spawns_f
                W_after = W - spawns_f * 10
                spawns_w_tmp = min(remaining_f // 2, W_after // 12)

                new_farm_count = total_f - 2 * spawns_f - 2 * spawns_w_tmp
                if new_farm_count >= min_farm:
                    spawns_w = spawns_w_tmp
                    farm_count = new_farm_count
                    break
                spawns_f -= 1

        # If wheat is not enough or there aren't enough farmers, revert to farming
        if W < 10 or total_f < 2 or spawns_f == 0:
            spawns_f = 0
            spawns_w = 0
            farm_count = total_f

        # Enforce minimum farming if possible
        if farm_count < min_farm:
            # Try to adjust to satisfy minimum farming
            farm_count = min_farm
            # Recompute spawns_f/spawns_w in a best-effort manner
            spawns_f = 0
            spawns_w = 0
            if total_f - min_farm >= 2:
                spawns_f = min((total_f - min_farm) // 2, max(0, W // 10))
                # Recompute spawns_w with updated spawns_f
                while spawns_f > 0:
                    remaining_f = total_f - 2 * spawns_f
                    W_after = W - spawns_f * 10
                    spawns_w_tmp = min(remaining_f // 2, W_after // 12)
                    if total_f - 2 * spawns_f - 2 * spawns_w_tmp >= min_farm:
                        spawns_w = spawns_w_tmp
                        break
                    spawns_f -= 1

        # Assign groups deterministically
        idx = 0
        # 1) Farmers into farm group
        if valid_farm:
            for i in range(min(farm_count, total_f)):
                environment.assign_group(farmers[i], farm_gid)
            idx = farm_count

        # 2) Spawn farmers
        if valid_spawn_f:
            for i in range(int(spawns_f)):
                if idx < total_f:
                    environment.assign_group(farmers[idx], spawn_f_gid)
                    idx += 1

        # 3) Spawn warriors
        if valid_spawn_w:
            for i in range(int(spawns_w)):
                if idx < total_f:
                    environment.assign_group(farmers[idx], spawn_w_gid)
                    idx += 1

        # 4) Remaining farmers go to farm
        while idx < total_f and valid_farm:
            environment.assign_group(farmers[idx], farm_gid)
            idx += 1

        # Warriors: all go to cave (attack)
        if valid_cave:
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