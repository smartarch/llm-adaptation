Reasoning and improved adaptation strategy

Goal: Increase the chance of killing the Dragon as fast as possible by making spawning decisions more aggressive and dynamic, while preserving the rule that all Warriors should be in the Cave to attack and Farmers stay in the Village to farm and spawn.

Key observations to improve:
- Spawning should be as aggressive as possible each turn given current resources (Farmers count and wheat) to grow both farms (wheat) and the army (new Farmers and Warriors) quickly.
- Always move all existing Warriors in the Village to the Cave so they can contribute to early damage, while Farmers remain in the Village to farm or spawn.
- Use a two-phase spawn calculation per turn:
  - First, spawn as many Farmers as possible (requires 2 Farmers per spawn and 10 wheat per spawn).
  - With the remaining Farmers and wheat, spawn as many Warriors as possible (requires 2 Farmers per spawn and 12 wheat per spawn).
- Any Farmers not used for spawning should be assigned to farming to sustain wheat production for future turns.
- In the Cave, keep Warriors in attack mode and move Farmers back to the Village.

This approach maximizes DPS quickly by expanding both the number of attackers (Warriors) and the wheat resource base (Farmers) while keeping the attack schedule consistent.

Python code

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Move all Warriors in the Village to the Cave to ensure immediate attack capability.
        # - Spawn as many new Farmers as possible given current Farmers and Wheat.
        # - With remaining Farmers and Wheat, spawn as many new Warriors as possible.
        # - Remaining Farmers (not used for spawning) stay in the Village to farm.

        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all existing Warriors in Village to Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # After this, all villagers left in Village are Farmers
        available_wheat = environment.farm.wheat

        F = len(farmers)

        # 2) Compute maximum spawns from Farmers and Wheat
        # Each spawn farmer consumes 2 farmers and 10 wheat
        max_f_spawns = min(F // 2, available_wheat // 10)

        # After Farmer spawns, update wheat and remaining farmers
        wheat_after_f_spawns = available_wheat - (max_f_spawns * 10)
        remaining_farmers = F - (max_f_spawns * 2)

        # Each Warrior spawn consumes 2 farmers and 12 wheat
        max_w_spawns = min(remaining_farmers // 2, wheat_after_f_spawns // 12)

        F_spawns = max_f_spawns
        W_spawns = max_w_spawns

        # 3) Assign spawns from Farmers
        idx = 0
        for _ in range(F_spawns):
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2

        for _ in range(W_spawns):
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        # 4) Remaining farmers go to farming
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