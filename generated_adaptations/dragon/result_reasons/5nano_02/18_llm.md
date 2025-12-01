Reasoning and improved adaptation strategy

Goal
- Push for even faster Dragon kills while preserving the core rules:
  - All Warriors must be in the Cave to attack.
  - Farmers stay in the Village to farm and spawn.
  - Spawns require 2 villagers and the appropriate wheat (10 for FarmerSpawn, 12 for WarriorSpawn).
  - Dragon can retaliate, so we want to grow DPS without risking a catastrophic Cave wipeout.
  - Objective is to reduce the average number of turns further (lower than 15.3 on average if possible).

Key ideas for improvement
- Keep Warriors in the Cave for immediate DPS, but tilt spawning decisions toward a dynamic, step-aware policy.
- Aggressive early spawns when resources and Dragon HP permit, but cap per-turn spawns at 2 per type.
- Introduce a targeted “double-push” early-turn override: if the Dragon is still strong and enough villagers/wheat exist, spawn both 2 Farmers and 2 Warriors in the same turn (subject to resources). This can significantly boost early DPS without sacrificing Wheat production in later turns.
- Ensure safe clamping so we never exceed available farmers and we always preserve some Wheat production for future turns.

What changes I’m making
- In assign_in_village:
  - Always move all Warriors in the Village to the Cave (to ensure early DPS).
  - Compute Farmer-spawns first (up to 2, bounded by F//2 and wheat//10).
  - Compute Warrior-spawns next with gating:
    - If there are at least 6 farmers left after Farmer-spawns and at least 24 Wheat left after Farmer-spawns, allow 2 Warrior-spawns.
    - Else if there are at least 4 farmers left and at least 12 Wheat left, allow 1 Warrior-spawn.
  - Added a strong but safe early-push override: if step <= 6 and Dragon HP > 40 and we can still spawn 2 Farmers and 2 Warriors, do it (resources permitting).
  - Clamp spawns to available farmers and cap 2 per type.
  - Remaining Farmers go to farming.
- In assign_in_cave:
  - Warriors stay in attack; Farmers go back to Village.

Python code

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Dynamic, tiered spawning strategy with an aggressive early push when safe

        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors in Village to Cave (immediate attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # After this, Village contains only Farmers (if any)
        available_wheat = environment.farm.wheat
        F = len(farmers)

        # 2) Compute Farmer-spawns (max 2)
        max_f_spawns_base = min(2, F // 2, available_wheat // 10)
        F_spawns = max_f_spawns_base

        wheat_after_f_spawns = available_wheat - (F_spawns * 10)
        remaining_f_after_f_spawns = F - (F_spawns * 2)

        # 3) Decide Warrior-spawns with gating
        W_spawns = 0
        if remaining_f_after_f_spawns >= 6 and wheat_after_f_spawns >= 24:
            W_spawns = 2
        elif remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12:
            W_spawns = 1

        # Optional strong early push: step <= 6 and dragon strong
        try:
            dragon_hp = environment.dragon.hp
            if step <= 6 and dragon_hp > 40 and W_spawns < 2 and remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12:
                # Try to push to 2 Warrior-spawns if resources permit
                W_spawns += 1
        except Exception:
            pass

        # Safety clamp: ensure we do not allocate more farmers than we have
        total_used = 2 * (F_spawns + W_spawns)
        if total_used > F:
            # Clamp: prioritize Farmer spawns
            max_pairs = F // 2
            F_spawns = min(F_spawns, max_pairs, 2)
            W_spawns = min(W_spawns, max(0, max_pairs - F_spawns))

        idx = 0
        # 4) Assign spawns from Farmers
        for _ in range(F_spawns):
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2

        for _ in range(W_spawns):
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        # 5) Remaining farmers go to farming
        for i in range(idx, len(farmers)):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Strategy in Cave:
        # - All Warriors in Cave should attack Dragon
        # - All Farmers in Cave should go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```