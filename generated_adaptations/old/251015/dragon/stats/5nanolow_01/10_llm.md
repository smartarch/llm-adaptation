Reasoning:
- The failures indicate the dragon is able to wipe out villagers faster than we can scale up. To improve, we should avoid over-committing villagers to spawning at the cost of having too few defenders in the cave, and we should maintain a small but steady defensive base in the village to sustain farming and future spawns.
- Updated strategy:
  - In the village:
    - Move all Warriors to the cave to attack.
    - Keep at least 2 Farmers in the village for ongoing farming and to provide a base for spawning in future turns.
    - Use wheat to spawn new Farmers first (spawn farmer requires 2 farmers and 10 wheat per spawn). But do not drop below 2 farmers remaining in the village.
    - With any remaining farmers and wheat, spawn Warriors (spawn warrior requires 2 farmers and 12 wheat per spawn).
  - In the cave:
    - All Warriors go to attack the Dragon.
    - Farmers return to the village to continue farming and to provide more spawning opportunities in subsequent turns.
- This approach aims for a safer balance: steady growth via spawning while preserving a minimal village defense, so the dragon damages fewer villagers upfront and we can threaten the dragon earlier with a larger attacking force in future steps.

Python code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Step 1: Send all Warriors to cave; keep at least 2 Farmers in village
        farmers_in_village = []
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                self.environment.assign_group(comp, "cave")
            else:
                farmers_in_village.append(comp)
                # By default, farmers stay in village
                self.environment.assign_group(comp, "farm")

        # Ensure we have at least 2 farmers in village for ongoing farming/spawning
        if len(farmers_in_village) <= 2:
            # Not enough farmers to spawn this turn; keep current assignments
            return

        # Step 2: Spawning planning based on current wheat
        total_wheat = int(getattr(environment.farm, "wheat", 0))

        # Keep at least 2 farmers in village; the rest are available for spawning
        available_for_spawning = farmers_in_village.copy()  # these are currently in "farm"

        # Reserve 2 farmers to stay in village (to maintain farm). 
        # We will pick from the pool of available farming villagers, but not drop below 2 total.
        # If len(available_for_spawning) <= 2, we already returned above.

        # Max possible "spawn farmer" spawns this turn
        max_spawn_farmer = min(len(available_for_spawning) - 2, total_wheat // 10 // 1)
        if max_spawn_farmer < 0:
            max_spawn_farmer = 0
        spawn_farmer_count = 2 * max_spawn_farmer

        # Assign the first 2*max_spawn_farmer farmers to "spawn farmer"
        for i in range(spawn_farmer_count):
            comp = available_for_spawning[i]
            self.environment.assign_group(comp, "spawn farmer")

        # Wheat remaining after spawning farmers
        wheat_after_farmer_spawns = total_wheat - (10 * max_spawn_farmer)

        # Remaining farmers after allocating to spawn farmers
        remaining_after_farmer_spawns = available_for_spawning[spawn_farmer_count:]

        # Max possible "spawn warrior" spawns with remaining farmers and wheat
        max_spawn_warrior = min(len(remaining_after_farmer_spawns) // 2, wheat_after_farmer_spawns // 12)
        spawn_warrior_count = 2 * max_spawn_warrior

        # Assign the next 2*max_spawn_warrior farmers to "spawn warrior"
        for i in range(spawn_warrior_count):
            comp = remaining_after_farmer_spawns[i]
            self.environment.assign_group(comp, "spawn warrior")

        # Any leftovers stay in their current groups (farm)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                self.environment.assign_group(comp, "attack")
            else:
                # Farmers return to the Village to continue farming/spawning
                self.environment.assign_group(comp, "village")
```