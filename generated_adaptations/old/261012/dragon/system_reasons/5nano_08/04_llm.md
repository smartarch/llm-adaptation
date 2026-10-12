Reasoning and adaptation strategy

Goal improvements:
- Increase early damage to the Dragon to reduce total turns.
- Ensure a steady, resource-backed spawn pipeline for both Farmers and Warriors.
- Keep all Warriors in the Cave to attack; keep Farmers in the Village for farming and spawning.
- Ensure at least one attack occurs within the first few steps and maintain a strong presence of Warriors in the Cave thereafter (at least half of them).

Key improvements over the previous approach:
- Greedy, resource-aware spawn planning:
  - Prioritize Warriors early because they deal higher damage (3 per attack) than Farmers (1 per attack).
  - Use two Farmers as “spawn warriors” only if there is enough wheat (12) to spawn and enough Farmers to spare.
  - After allocating Warrior-spawn capacity, use remaining Farmers to spawn Farmers (needs 10 wheat per spawn).
  - This yields new Warriors quickly while continuing to grow the overall population with new Farmers, balancing DPS and survivability.
- Deterministic movement:
  - All existing Warriors are moved to the Cave to guarantee immediate attack potential.
  - Spawners remain in the Village and continue to spawn as wheat accumulates.
- Cave phase:
  - All Warriors in the Cave are placed in the “attack” group to maximize DPS on the Dragon each turn.

Strategy outline:
- In assign_in_village:
  - Move all existing Warriors to the Cave (to start attacking).
  - Read current wheat from environment.farm.wheat.
  - Compute the maximum Warrior spawns: min(number_of_farmers // 2, wheat // 12).
  - After reserving Farmers for Warrior-spawns, compute remaining wheat.
  - Compute the maximum Farmer spawns with the remaining wheat: min(remaining_farmers // 2, remaining_wheat // 10).
  - Assign the first 2* Warrior-spawners to "spawn warrior".
  - Assign the next 2* Farmer-spawners to "spawn farmer".
  - Assign all remaining Farmers to "farm".
  - Warriors are already moved to the Cave and will attack in the cave stage.
- In assign_in_cave:
  - Warrior -> "attack"
  - Farmer -> "village"
  - Other edge cases default to "cave" (safety)

This approach aims to have at least one Warrior in the Cave early (and more quickly over time), while maintaining a growing population and wheat supply to sustain spawning. It should improve the average number of steps to kill the Dragon and increase the win rate.

Code implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Gather current villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Ensure all existing Warriors move to the Cave to start attacking
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning among Farmers
        # Current wheat available in the Farm
        wheat = 0
        if hasattr(environment, "farm") and environment.farm is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        # Determine Warrior spawns first:
        # Each Warrior spawn requires 2 Farmers (spawners) and 12 wheat.
        max_warrior_spawns = min(len(farmers) // 2, wheat // 12)

        # Reserve Farmers used for Warrior spawns
        spawner_for_warriors = 2 * max_warrior_spawns
        remaining_farmers = len(farmers) - spawner_for_warriors

        # Wheat left after Warrior spawns
        wheat_after_warrior_spawns = max(0, wheat - max_warrior_spawns * 12)

        # Determine Farmer spawns with remaining wheat
        max_farmer_spawns = min(remaining_farmers // 2, wheat_after_warrior_spawns // 10)
        spawner_for_farmers = 2 * max_farmer_spawns

        # 3) Assign groups for Farmers
        # Order: first spawner_for_warriors -> "spawn warrior",
        # then spawner_for_farmers -> "spawn farmer",
        # rest -> "farm"
        total_farmers = len(farmers)

        for i, c in enumerate(farmers):
            if i < spawner_for_warriors:
                environment.assign_group(c, "spawn warrior")
            elif i < spawner_for_warriors + spawner_for_farmers:
                environment.assign_group(c, "spawn farmer")
            else:
                environment.assign_group(c, "farm")

        # Note: Warriors have already been moved to the cave above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, map roles to actions
        for c in components:
            role = getattr(c, "role", None)

            if role == "Warrior":
                # Attack the Dragon
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                # Return Farmers to Village
                environment.assign_group(c, "village")
            else:
                # Fallback: stay in cave
                environment.assign_group(c, "cave")
```