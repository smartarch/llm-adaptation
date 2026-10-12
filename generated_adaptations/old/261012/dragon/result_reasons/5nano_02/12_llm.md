Reasoning and improved adaptation strategy

Goal recap:
- Kill the Dragon as fast as possible, ideally in fewer turns than before.
- Maintain core constraints: all Warriors should be in the Cave to attack; Farmers stay in the Village to farm or spawn; Spawns require 2 villagers and the appropriate wheat (10 for FarmerSpawn, 12 for WarriorSpawn); Dragon can retaliate and you must avoid wiping out too many villagers; Dragon must die within 30 steps.

What tends to help to reduce turns:
- Increase early DPS without starving wheat production.
- Keep Warriors in the Cave and attacking as soon as possible.
- Spawn farmers to grow wheat, and spawn warriors to grow DPS, but do so with a cautious, tie-breaking policy so you don’t over-commit to spawning when resources or future wheat production would be compromised.

Strategy changes I’m proposing now:
- Move all existing Warriors in the Village to the Cave every turn (as before) to guarantee early DPS.
- Spawning policy (greedy but gated):
  - First, spawn as many Farmer-spawns as possible (up to 2 per turn) given current farmers and wheat: F_spawns = min(2, F // 2, wheat // 10).
  - Compute remaining farmers and wheat after Farmer-spawns.
  - Decide Warrior-spawns with a safety gate:
    - If there are at least 6 remaining farmers and at least 24 wheat left after Farmer-spawns, allow 2 Warrior-spawns.
    - Else if there are at least 4 remaining farmers and at least 12 wheat left, allow 1 Warrior-spawn.
  - Additionally, apply a light step-based aggressiveness: if step <= 9 and dragon HP is very high (> 40), allow pushing the Warrior-spawns up by 1 if possible (still capped at 2); this helps accelerate early DPS when the dragon is strongest.
  - Ensure we do not exceed the available farmers (clamp if needed) and do not exceed 2 spawns per type.
- After spawns, remaining farmers go to farming in Village; Warriors in Cave stay in attack mode.

This approach aims to get a higher DPS earlier (to shave turns) but with safeguards to avoid blowing up the Cave with too many villagers at once and starving future wheat.

Python code

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Tiered but gated aggressive spawning strategy:
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
        max_f_spawns_base = min(2, F // 2, available_wheat // 10)
        F_spawns = max_f_spawns_base

        wheat_after_f_spawns = available_wheat - (F_spawns * 10)
        remaining_f_after_f_spawns = F - (F_spawns * 2)

        # 3) Decide Warrior-spawns with safety gates
        W_spawns = 0
        if remaining_f_after_f_spawns >= 6 and wheat_after_f_spawns >= 24:
            W_spawns = 2
        elif remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12:
            W_spawns = 1

        # Light aggressiveness: if early and dragon is strong, push one more Warrior-spawn if possible
        try:
            dragon_hp = environment.dragon.hp
            if step <= 9 and dragon_hp > 40 and W_spawns < 2 and remaining_f_after_f_spawns - (W_spawns * 2) >= 2 and wheat_after_f_spawns - (W_spawns * 12) >= 12:
                W_spawns += 1
        except Exception:
            pass

        # Safety clamp: ensure within available farmers
        total_used_villagers = 2 * (F_spawns + W_spawns)
        if total_used_villagers > F:
            # Clamp: prioritize Farmer spawns
            max_pairs = F // 2
            F_spawns = min(F_spawns, max_pairs, 2)
            W_spawns = min(W_spawns, max(0, max_pairs - F_spawns))

        # Recompute indices after clamping
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