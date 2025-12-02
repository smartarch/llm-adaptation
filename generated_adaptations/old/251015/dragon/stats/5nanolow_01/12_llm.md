Reasoning:
- The repeated failures indicate we need a safer, more consistent growth while maintaining a minimal defensive line in the village. A robust approach is to:
  - Keep all Warriors in the Cave to attack (they are the primary damage dealers).
  - Keep a small but steady core of Farmers in the Village (to farm wheat and enable spawning).
  - Use wheat to spawn new Farmers first (to grow long-term wheat production), but never drop below a minimal village workforce (to sustain growth and prevent collapse).
  - With any remaining Farmers and Wheat, spawn Warriors to increase attacking power for future turns.
- This balances short-term defense with long-term scaling, aiming to improve win rate and reduce turns to victory.

Python code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Step A: Move all Warriors to cave; keep a safe core of Farmers in village
        farmers_in_village = []
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                self.environment.assign_group(comp, "cave")
            else:
                farmers_in_village.append(comp)
                self.environment.assign_group(comp, "farm")

        # Step B: Ensure a minimal farming backbone in village
        MIN_FARMERS_IN_VILLAGE = 3
        if len(farmers_in_village) < MIN_FARMERS_IN_VILLAGE:
            # Not enough farmers to safely spawn this turn; do not split further
            return

        # Step C: Spawning planning based on current wheat
        total_wheat = int(getattr(environment.farm, "wheat", 0))

        # Farmers available for spawning (beyond the minimal village backbone)
        available_for_spawning = farmers_in_village.copy()
        # Reserve MIN_FARMERS_IN_VILLAGE to stay in village
        reserves = min(len(available_for_spawning), MIN_FARMERS_IN_VILLAGE)
        if reserves > 0:
            # ensure at least MIN_FARMERS_IN_VILLAGE remain in village by not touching them
            available_for_spawning = available_for_spawning[:-0]  # explicit for clarity

        # Compute spawns for Farmers first
        max_spawn_farmer = min(len(available_for_spawning) // 2, total_wheat // 10)
        spawn_farmer_count = 2 * max_spawn_farmer

        # Assign 2*max_spawn_farmer farmers to "spawn farmer"
        for i in range(spawn_farmer_count):
            comp = available_for_spawning[i]
            self.environment.assign_group(comp, "spawn farmer")

        # Wheat remaining after spawning farmers
        wheat_after_farmer_spawns = total_wheat - (10 * max_spawn_farmer)

        # Remaining farmers after allocating to spawn farmers
        remaining_after_farmer_spawns = available_for_spawning[spawn_farmer_count:]

        # Spawn Warriors with remaining farmers and wheat
        max_spawn_warrior = min(len(remaining_after_farmer_spawns) // 2,
                                wheat_after_farmer_spawns // 12)
        spawn_warrior_count = 2 * max_spawn_warrior

        for i in range(spawn_warrior_count):
            comp = remaining_after_farmer_spawns[i]
            self.environment.assign_group(comp, "spawn warrior")

        # Leftover farmers stay in their current groups (farm)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                self.environment.assign_group(comp, "attack")
            else:
                # Farmers return to the Village
                self.environment.assign_group(comp, "village")
```