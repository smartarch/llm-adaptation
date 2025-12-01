Reasoning and improved adaptation strategy

Goal
- Push for even faster Dragon kills while preserving the core rules:
  - All Warriors must be in the Cave to attack.
  - Farmers stay in the Village to farm and spawn.
  - Spawns require 2 villagers and the appropriate wheat (10 for FarmerSpawn, 12 for WarriorSpawn).
  - Dragon can retaliate, so we want to grow DPS without risking a catastrophic Cave wipeout.
  - Objective is to reduce the average number of turns further (lower than 15.3 on average if possible).

Key ideas for improvement
- Keep Warriors in the Cave for immediate DPS, but tune spawning decisions to be more dynamic and step-aware.
- Use a tiered, dynamic spawning policy that adapts to:
  - How many Farmers are available
  - How much wheat is available
  - What step we are in (early vs late game)
  - How strong the Dragon still is (HP)
- Cap spawns at most 2 per type per turn and apply safeguards to avoid starving wheat production.
- Make spawning more aggressive on favorable turns, but inject a small “step-aware” guard to avoid overloading the Cave when resources are tight.

What changes I’m making
- In assign_in_village:
  - Always move all Warriors in the Village to the Cave (mandatory).
  - Compute Farmer-spawns first (up to 2, bounded by F//2 and wheat//10).
  - Compute Warrior-spawns with a dynamic, step-aware gating:
    - If turns_left > 15 and dragon HP is high (> 40):
      - If at least 6 farmers remain after Farmer-spawns and at least 24 wheat remain, allow 2 Warrior-spawns.
      - Else if at least 4 farmers remain and at least 12 wheat remain, allow 1 Warrior-spawn.
      - Additionally, as a strong early push, if step <= 6, dragon HP > 40, and resources allow, try to add an extra Warrior-spawn (up to 2 total).
    - If turns_left <= 15 (late game), fall back to a safer gating:
      - If remaining_f_after_f_spawns >= 6 and wheat_after_f_spawns >= 24, allow 2 Warrior-spawns.
      - Else if remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12, allow 1 Warrior-spawn.
  - Clamp spawns to the number of available Farmers (2 per type max).
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
        # Dynamic, tiered spawning strategy with step-aware gating

        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors in Village to Cave (immediate attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # After this, Village contains only Farmers (if any)
        available_wheat = environment.farm.wheat
        F = len(farmers)

        # 2) Farmer-spawns: up to 2, bounded by F//2 and wheat//10
        max_f_spawns_base = min(2, F // 2, available_wheat // 10)
        F_spawns = max_f_spawns_base

        wheat_after_f_spawns = available_wheat - (F_spawns * 10)
        remaining_f_after_f_spawns = F - (F_spawns * 2)

        # 3) Warrior-spawns: gated by resources and step/HP
        W_spawns = 0
        turns_left = 30 - step  # how many turns left until 30
        try:
            dragon_hp = environment.dragon.hp
        except Exception:
            dragon_hp = 0

        if turns_left > 15 and dragon_hp > 40:
            if remaining_f_after_f_spawns >= 6 and wheat_after_f_spawns >= 24:
                W_spawns = 2
            elif remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12:
                W_spawns = 1
            # Strong early push: if resources allow, push to 2
            if step <= 6 and W_spawns < 2 and remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12:
                W_spawns += 1
        else:
            # Late-game gating (safer)
            if remaining_f_after_f_spawns >= 6 and wheat_after_f_spawns >= 24:
                W_spawns = 2
            elif remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12:
                W_spawns = 1

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