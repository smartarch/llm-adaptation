```py
"""
Improved adaptation strategy

Rationale:
- The Dragon can retaliate and can wipe out villagers in the cave, so we want to keep a
  stable farming base while accelerating offensive power.
- Previous approach aggressively spawned whenever possible, but it can stall attack momentum
  early or risk excessive cave casualties if dragon retaliates with many cave villagers.
- Improved strategy uses a step-aware, greedy spawning plan:
  1) All Warriors should always go to the Cave to attack.
  2) Farmers primarily farm to grow wheat. When enough wheat is available, spawn as many
     Farmers as possible to accelerate wheat production (spawn farmer). Only after that
     should we consider spawning Warriors (spawn warrior) to increase offensive pressure.
  3) We allow step-aware nuance: in early steps we prioritize farmer spawns to boost wheat
     growth; in later steps, we also spawn warriors if wheat permits.
- This balances growth and attack power, aiming to kill the dragon faster while preserving
  villagers from catastrophic dragon retaliation.

Implementation notes:
- In assign_in_village:
  - Gather farmers and warriors present in the village.
  - Move all warriors to the cave (attack path).
  - Compute maximum possible spawns for farmers (spawn farmer) based on wheat and farmer count.
  - After allocating farmer spawns, compute maximum possible spawns for warriors (spawn warrior)
    using the remaining farmers and wheat (only after step >= 3, to emphasize early growth).
  - Assign 2*spawn_farmers farmers to "spawn farmer".
  - Assign 2*spawn_warriors farmers to "spawn warrior".
  - Remaining farmers go to "farm".
- In assign_in_cave:
  - All Warriors go to "attack".
  - Farmers go to "village" (to continue farming or cycling back for spawns).

This approach aims for steady wheat growth early and a progressive ramp-up of attack power, reducing the chance of losing before the dragon dies.

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by current role
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
        wheat_after_farm = max(0, wheat - max_farm_spawn * 10)

        # Remaining farmers after allocating 2 per farmer-spawn
        remaining_farmers = F - max_farm_spawn * 2

        # 2) Warrior spawns: only consider after some growth (prefer later steps)
        max_war_spawn = 0
        if step >= 3:
            max_war_spawn = min(remaining_farmers // 2, wheat_after_farm // 12)

        # Assign: move all Warriors to cave
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

        # 5) Remaining farmers go to farming
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