```py
"""
SmartAdaptation v2: step-aware spawning to accelerate kill while preserving early survivability

Rationale:
- All Warriors should be in the Cave to attack the Dragon.
- Farmers keep farming to grow Wheat, enabling spawn events.
- Spawns consume Wheat and require 2 villagers in the respective spawn group.
- Early on we prioritize Wheat growth (farm spawns) to unlock more powerful spawns later.
- Starting from step 2, we enable Warrior spawns as soon as Wheat and available Farmers allow.
- This aims to ramp up DPS earlier without starving Wheat production.

Adaptation details:
- assign_in_village:
  - Move all Warriors to the Cave.
  - Compute how many Farm spawns we can attempt: max_farm_spawn = min(F // 2, Wheat // 10).
  - After reserving Wheat for farm spawns, compute remaining Wheat and Farmers.
  - If step >= 2, compute max_war_spawn = min(remaining_farmers // 2, Wheat_left // 12).
  - Otherwise, max_war_spawn = 0 (early steps focus on farming).
  - Assign 2*max_farm_spawn Farmers to "spawn farmer".
  - Assign 2*max_war_spawn Farmers to "spawn warrior".
  - Remaining Farmers to "farm".
- assign_in_cave:
  - Warrior components -> "attack"
  - Farmer components -> "village"

This version preserves the rule that all Warriors must go to the Cave, and uses a simple yet adaptive plan to ramp up spawning over time.

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by current role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)
        W = len(warriors)

        # Wheat available at the Farm
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        # Step-aware spawning strategy
        # 1) Farmer spawns: as many as possible given 2 farmers per event and 10 wheat per event
        max_farm_spawn = min(F // 2, wheat // 10)

        # Wheat left after farmer spawns
        wheat_left_after_farm = max(0, wheat - max_farm_spawn * 10)

        # Remaining farmers after allocating 2 per farmer-spawn
        remaining_farmers = F - max_farm_spawn * 2

        # 2) Warrior spawns: only after step 2 (early steps emphasize farming)
        max_war_spawn = 0
        if step >= 2:
            max_war_spawn = min(remaining_farmers // 2, wheat_left_after_farm // 12)

        # Assign: move all Warriors to Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 3) Assign 2*max_farm_spawn farmers to "spawn farmer"
        idx = 0
        to_spawn_farmers = max_farm_spawn * 2
        for _ in range(to_spawn_farmers):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # 4) Assign 2*max_war_spawn farmers to "spawn warrior"
        to_spawn_warriors = max_war_spawn * 2
        for _ in range(to_spawn_war_spawn):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # 5) Remaining farmers go to "farm"
        for j in range(idx, F):
            environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack, Farmers should return to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```