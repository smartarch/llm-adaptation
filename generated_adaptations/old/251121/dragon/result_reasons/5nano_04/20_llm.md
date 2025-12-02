Reasoning and updated strategy

Goal
- Increase the chance to kill the Dragon sooner by delivering early, but controlled, Dragon DPS while maintaining a robust wheat-based growth pipeline.
- Avoid reckless spawning that wastes wheat or floods the cave with troops and causes excessive casualties.
- Ensure the Dragon is attacked early and sustain DPS through a steady population growth (Farmers and Warriors).

Key ideas in this iteration
- Step-aware, adaptive Warrior deployment: instead of pushing a fixed number of Warriors to the Cave every step, we escalate deployment gradually as steps progress (with a cap). If the Dragon looks weakened (low HP), we can push a bit more aggressively, but we still avoid flooding the Cave too early.
- Budgeted spawning with disjoint pairs: per step, spawn up to a small number of Farmer pairs (2 Farmers per spawn, 10 wheat per spawn) and then, with the remaining Farmers and wheat, spawn Warrior pairs (2 Farmers per spawn, 12 wheat per spawn). Each step uses disjoint farmer pairs to avoid reusing the same villagers for multiple spawns.
- Farmers stay in the Village to farm and provide wheat; Warriors move to the Cave to attack. In the Cave, Warriors attack and Farmers return to the Village when the stage is over.
- This approach aims to kill the Dragon earlier (within the first 15 steps if possible) while building a sustainable DPS pipeline for later steps.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Step-aware escalation with budgeted spawning
        if not components:
            return

        # Split villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Gradually move Warriors to the Cave
        if len(warriors) > 0:
            # Cap grows as steps progress: 1, 2, 3, 4, ...
            move_cap = min(len(warriors), max(1, min(4, step + 1)))
            for i in range(move_cap):
                environment.assign_group(warriors[i], "cave")

        # 2) Keep Farmers in the Village (farm)
        for c in farmers:
            environment.assign_group(c, "farm")

        # 3) Aggressive, budgeted spawning (per step)
        wheat = getattr(environment.farm, "wheat", 0)

        # Farmer spawns: 2 farmers per spawn, 10 wheat per spawn
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)
        max_farm_spawns = min(max_farm_spawns, 3)  # cap per-step spawns

        # Trigger farmer spawns using disjoint farmer pairs
        for i in range(max_farm_spawns):
            c1 = farmers[2 * i]
            c2 = farmers[2 * i + 1]
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")

        # Update wheat budget after farmer spawns
        wheat_after_farm = wheat - max_farm_spawns * 10
        idx_after_farm = 2 * max_farm_spawns

        remaining_farmers_for_war = len(farmers) - idx_after_farm

        # Warrior spawns: 2 farmers per spawn, 12 wheat per spawn
        max_war_spawns = min(remaining_farmers_for_war // 2, wheat_after_farm // 12)
        max_war_spawns = min(max_war_spawns, 2)  # cap per-step spawns

        # Trigger warrior spawns using disjoint farmer pairs after farmer-spawns
        for i in range(max_war_spawns):
            c1 = farmers[idx_after_farm + 2 * i]
            c2 = farmers[idx_after_farm + 2 * i + 1]
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave:
        # - All Warriors should attack (group "attack").
        # - All Farmers should go back to the Village (group "village").
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```