Reasoning and improved adaptation strategy

Goal
- Kill the Dragon as fast as possible while keeping within the rules:
  - All Warriors must be in the Cave to attack.
  - Farmers stay in the Village to farm and spawn.
  - Spawns require 2 villagers and the appropriate wheat (10 for FarmerSpawn, 12 for WarriorSpawn).
  - Dragon can retaliate, so we want to grow DPS without letting the Cave get wiped out.
  - Aim to reduce the average number of turns further (ideally below the previous best).

Key ideas for improvement
- Maintain the core constraint (Warriors in Cave; Farmers in Village) but push for stronger early DPS by slightly more aggressive spawning on favorable turns.
- Use a tiered, dynamic spawning policy that depends on:
  - How many Farmers are available
  - How much wheat is available
  - How many steps have passed
  - How strong the Dragon currently is (HP)
- Cap spawns at 2 per type per turn (as required), but apply a small early-turn aggressiveness when the Dragon is still strong and resources allow, to boost early DPS without compromising Wheat production in later turns.
- Keep Farmers in Village to farm or spawn, and send Warriors to the Cave immediately.

What changes I’m making
- In assign_in_village:
  - Move all existing Warriors in the Village to the Cave (to ensure early DPS).
  - Compute Farmer-spawns first (up to 2, bounded by F//2 and wheat//10).
  - Compute Warrior-spawns next with a gating policy:
    - If at least 6 farmers remain and at least 24 wheat remain after Farmer-spawns, allow 2 Warrior-spawns.
    - Else if at least 4 farmers remain and at least 12 wheat remain after Farmer-spawns, allow 1 Warrior-spawn.
  - Add a small early-aggressiveness nudge: if step <= 4 and Dragon HP > 40 and we can still spawn another Warrior (without breaking limits), grant +1 Warrior-spawn (subject to cap 2).
  - Clamp spawns to the number of available farmers.
  - Spawn Farmers and Warriors from the village farmers, remaining farmers go to farming.
- In assign_in_cave: keep Warriors in "attack" and move Farmers back to "village".

Python code

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Tiered, gated aggressive spawning strategy:
        # - Move all Warriors in Village to Cave (immediate attack)
        # - Spawn Farmer-spawns first (max 2)
        # - Then decide Warrior-spawns with safety gates (max 2)
        # - Optional light aggression when dragon is strong early on
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
        max_f_spawns = min(2, F // 2, available_wheat // 10)
        F_spawns = max_f_spawns

        wheat_after_f_spawns = available_wheat - (F_spawns * 10)
        remaining_f_after_f_spawns = F - (F_spawns * 2)

        # 3) Decide Warrior-spawns with safety gates
        W_spawns = 0
        if remaining_f_after_f_spawns >= 6 and wheat_after_f_spawns >= 24:
            W_spawns = 2
        elif remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12:
            W_spawns = 1

        # Extra aggressive nudge early
        try:
            dragon_hp = environment.dragon.hp
            if step <= 4 and dragon_hp > 40 and W_spawns < 2 and remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12:
                W_spawns += 1
        except Exception:
            pass

        total_used = 2 * (F_spawns + W_spawns)
        if total_used > F:
            # Clamp: prioritize Farmer spawns
            max_pairs = F // 2
            F_spawns = min(F_spawns, max_pairs)
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