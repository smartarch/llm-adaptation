Reasoning:
- The recurring failures show that the dragon can wipe out villagers before we can build a sufficient attacking force. A safer and potentially more effective strategy is:
  - In the village: keep a steady core of farmers (minimum floor) to ensure ongoing wheat production. Move all Warriors to the cave to contribute to early damage.
  - Use wheat to spawn farmers first, but never drop below the minimum village farmers. This ensures growth and future spawning capability.
  - With any remaining farmers and wheat, spawn additional warriors to increase attacking power for future turns.
  - In the cave: send all warriors to attack and send farmers back to village to continue farming/spawning.
- This approach emphasizes safe, incremental growth with a guaranteed defensive base and gradual scale-up of attackers, aiming to kill the dragon faster in later turns.

Python code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Step 1: Move all Warriors to cave; keep a safe core of Farmers in village
        farmers_in_village = []
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                self.environment.assign_group(comp, "cave")
            else:
                farmers_in_village.append(comp)
                self.environment.assign_group(comp, "farm")

        # Step 2: Ensure a minimal farming backbone in the village
        MIN_FARMERS_IN_VILLAGE = 3
        if len(farmers_in_village) < MIN_FARMERS_IN_VILLAGE:
            # Not enough farmers to spawn safely this turn; skip spawning
            return

        # Step 3: Spawning planning based on current wheat
        total_wheat = int(getattr(environment.farm, "wheat", 0))

        # Farmers available for spawning (these are in village)
        available_for_spawning = list(farmers_in_village)

        # Reserve at least MIN_FARMERS_IN_VILLAGE to stay in village
        # We consider the first MIN_FARMERS_IN_VILLAGE as protected and unused for spawning
        if len(available_for_spawning) <= MIN_FARMERS_IN_VILLAGE:
            # No extra farmers to spawn this turn
            return
        spawning_pool = available_for_spawning[MIN_FARMERS_IN_VILLAGE:]

        # Compute spawns for Farmers first
        max_spawn_farmer = min(len(spawning_pool) // 2, total_wheat // 10)
        spawn_farmer_count = 2 * max_spawn_farmer

        # Assign 2*max_spawn_farmer farmers to "spawn farmer"
        for i in range(spawn_farmer_count):
            comp = spawning_pool[i]
            self.environment.assign_group(comp, "spawn farmer")

        # Wheat remaining after spawning farmers
        wheat_after_farmer_spawns = total_wheat - (10 * max_spawn_farmer)

        # Remaining farmers after allocating to spawn farmers
        remaining_after_farmer_spawns = spawning_pool[spawn_farmer_count:]

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
                # Warriors attack the Dragon
                self.environment.assign_group(comp, "attack")
            else:
                # Farmers return to the Village to continue farming/spawning
                self.environment.assign_group(comp, "village")
```