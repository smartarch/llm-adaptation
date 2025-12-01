Reasoning and improved adaptation strategy

Goal
- Further reduce the number of turns to kill the Dragon while keeping the core rules:
  - All Warriors must be in the Cave to attack.
  - Farmers stay in the Village to farm and spawn.
  - Spawns require 2 villagers and the appropriate wheat (10 for FarmerSpawn, 12 for WarriorSpawn).
  - Dragon can retaliate, so we want to grow DPS without letting the Cave get wiped out.
  - Aim to reduce the average turns even further (lower than 15.3 on average).

What tends to help to reduce turns
- Maintain Warriors in the Cave for immediate DPS, but improve early growth by making spawns dynamic and step-aware.
- Use a tiered, dynamic spawning policy that adapts to:
  - How many Farmers are available
  - How much wheat is available
  - What step we are in (early vs late game)
  - How strong the Dragon still is (HP)
- Cap spawns to at most 2 of each type per turn (as required) and apply safeguards to avoid starving wheat production or overpopulating the Cave.
- Prefer early Farmer-spawns to boost wheat production, then use remaining resources to spawn Warriors for DPS, with a small early aggressiveness boost if the Dragon is very strong and early in the game.

What changes I’m making
- In assign_in_village:
  - Always move all Warriors in the Village to the Cave (maintain the rule).
  - Compute Farmer-spawns first (up to 2, bounded by F//2 and wheat//10).
  - Compute Warrior-spawns next with dynamic gating:
    - If there are at least 6 Farmers left after Farmer-spawns and at least 24 Wheat left after Farmer-spawns, allow up to 2 Warrior-spawns.
    - Else if there are at least 4 Farmers left and at least 12 Wheat left, allow 1 Warrior-spawn.
    - Additionally, a small early aggression nudge: if step <= 4 and Dragon HP > 40 and a Warrior-spawn is not already at 2, allow one extra Warrior-spawn when resources permit.
  - Clamp spawns to the number of available Farmers (2 per type max).
  - The remaining Farmers go to farming.
- In assign_in_cave:
  - All Warriors in Cave go to "attack" to hit the Dragon.
  - All Farmers in Cave go back to the Village.

This approach aims to push a bit more DPS earlier when it’s safe (early turns with ample resources and strong dragon), while preserving the safety of the Wheat pipeline and avoiding excessive losses in the Cave.

Python code

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Dynamic, tiered spawning strategy:
        # - Move all Warriors in Village to Cave (immediate attack)
        # - Spawn Farmer-spawns first (max 2)
        # - Then decide Warrior-spawns with gating (max 2)
        # - Optional light aggressiveness early when dragon is strong
        # - Remaining Farmers go to farming

        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all existing Warriors in Village to Cave
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

        # Optional light aggressiveness early
        try:
            dragon_hp = environment.dragon.hp
            if step <= 4 and dragon_hp > 40 and W_spawns < 2 and remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12:
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