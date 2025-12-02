Reasoning and updated strategy

What we learned:
- The game reward is early and sustained Dragon DPS, plus growth of the population to sustain that DPS through spawning.
- Previous implementations sometimes over-spawned within a single step (not accounting for wheat budget after each spawn), and/or did not aggressively push enough Warriors into the Cave early enough.

Key adjustments in this iteration:
- Correct wheat budgeting per step. When spawning, we now:
  - Compute how many Farmer spawns we can trigger given 2 farmers per spawn and 10 wheat per spawn.
  - Deduct the used wheat from the budget before calculating Warrior spawns, then compute how many Warrior spawns we can trigger with the remaining wheat and available farmers (2 farmers per Warrior spawn and 12 wheat per spawn).
  - Apply spawns in a single step using disjoint sets of farmers, ensuring no double-use of farmers in the same step.
- Maintain the requirement that all Warriors go to the Cave (to attack the Dragon) and Farmers stay in the Village (for farming/spawning).
- Ensure Warriors are sent to the Cave as soon as possible, so the Dragon is attacked early (despite potential counter-attacks).

This approach aims to:
- Get the Dragon attacked within the first 15 steps by having Warriors move to the Cave early.
- Exploit Wheat to quickly grow both Farmers and Warriors in parallel, increasing DPS over time.
- Keep a steady pipeline of DPS in the Cave (half or more Warriors present there over time).

Code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Aggressive spawning with correct wheat budgeting.
        # - Move all Warriors to the Cave (they will attack once there).
        # - Keep Farmers farming (in the village) and use wheat to spawn more Farmers and Warriors.
        if not components:
            return

        # Classify villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors to the cave (towards the Dragon)
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Keep Farmers in the Village (farming)
        for c in farmers:
            environment.assign_group(c, "farm")

        # 3) Aggressive, budgeted spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Farmer spawns: need 2 farmers and 10 wheat per spawn
        n_farm_spawns = min(len(farmers) // 2, wheat // 10)

        # Trigger farmer spawns
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

        # Trigger warrior spawns
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