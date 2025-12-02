Reasoning and updated strategy

Goal and rationale:
- We need a faster, more reliable kill by delivering early Dragon DPS while growing the population to sustain DPS over time.
- Key levers: move Warriors to the Cave quickly but not too aggressively to avoid crushing casualties from the Dragon’s counterattacks, and grow both Farmers (for wheat) and Warriors (for DPS) using wheat-fed spawning.
- Strategy improvements:
  - Step-aware escalation: in assign_in_village, move Warriors to the Cave gradually as steps progress (to avoid large early losses while still building early DPS).
  - Per-step, budgeted spawning: spawn Farmers and Warriors in a careful sequence using available wheat, with explicit caps per step to prevent over-spawning in a single step. This preserves wheat for ongoing growth across many steps.
  - In the Cave, keep Warriors focused on attacking (attack group) and keep Farmers returning to the Village (village group) to continue producing wheat.
  - The approach aims to have Dragon attacked early (within the first few steps) and then sustain DPS with a growing army, while keeping a reasonable number of Farmers in the Village to keep wheat flowing.

What changes:
- assign_in_village:
  - Move up to a gradually increasing number of Warriors to the Cave each step (based on step, capped by how many Warriors exist).
  - Keep all Farmers in the Village (farm) by default.
  - Spawn Farmer pairs using wheat in a budgeted way (up to 3 spawns per step, 2 Farmers per spawn, 10 wheat per spawn).
  - After farmer spawns, spawn Warrior pairs using remaining Farmers and remaining wheat (up to 2 Warrior spawns per step, 2 Farmers per spawn, 12 wheat per spawn).
- assign_in_cave:
  - All Warriors in the Cave should attack the Dragon (attack).
  - All Farmers in the Cave should go back to the Village (village).

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

        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Gradually move Warriors to the Cave
        # Increase the number moved per step as steps progress
        if len(warriors) > 0:
            move_cap = min(max(1, step // 2 + 1), len(warriors))  # 1,1,2,2,3,3,... growth
            for i in range(move_cap):
                environment.assign_group(warriors[i], "cave")

        # 2) Keep Farmers in Village (farm by default)
        for c in farmers:
            environment.assign_group(c, "farm")

        # 3) Aggressive, budgeted spawning (per step)
        wheat = getattr(environment.farm, "wheat", 0)

        # Farmer spawns: need 2 farmers and 10 wheat per spawn
        n_farm_spawns = min(len(farmers) // 2, wheat // 10)
        # Cap per-step spawns to avoid over-spawning in one step
        n_farm_spawns = min(n_farm_spawns, 3)

        # Trigger farmer spawns using disjoint farmer pairs
        for i in range(n_farm_spawns):
            c1 = farmers[2 * i]
            c2 = farmers[2 * i + 1]
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")

        # Update wheat budget after farmer spawns
        wheat_after_farm = wheat - n_farm_spawns * 10
        idx_after_farm = 2 * n_farm_spawns

        remaining_farmers_for_war = len(farmers) - idx_after_farm

        # Warrior spawns: need 2 farmers and 12 wheat per spawn
        n_war_spawns = min(remaining_farmers_for_war // 2, wheat_after_farm // 12)
        n_war_spawns = min(n_war_spawns, 2)  # cap per-step to avoid over-spawning

        # Trigger warrior spawns using disjoint farmer pairs after farmers for farmer-spawns
        for i in range(n_war_spawns):
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