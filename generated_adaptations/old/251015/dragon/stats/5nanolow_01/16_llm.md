Reasoning:
- The recurring failures show that dragons wipe out villagers too quickly and our spawning is not producing enough attackers fast enough. A safer, more consistent growth pattern is needed:
  - Keep all Warriors in the Cave to contribute to early damage.
  - Maintain a small but steady core of Farmers in the Village (minimum floor) to continuously farm wheat and enable spawning.
  - Spawn Farmers first using available wheat, but never drop below the minimum village Farm workforce.
  - With remaining Farmers and wheat, spawn Warriors to increase attacking power in future turns.
  - In the Cave, send Warriors to attack and send Farmers back to the Village to continue farming/spawning.

This approach aims for a reliable build-up: defend the Village with a small core, grow the population via spawning as soon as wheat allows, then progressively increase the attacking force in the Cave.

Python code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Step 1: Move all Warriors to the Cave; keep Farmers in Village
        farmers_in_village = []
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                self.environment.assign_group(comp, "cave")
            else:
                farmers_in_village.append(comp)
                self.environment.assign_group(comp, "farm")

        # Step 2: Ensure a minimal farming backbone in the village
        MIN_VILLAGE_FARMERS = 3
        if len(farmers_in_village) < MIN_VILLAGE_FARMERS:
            # Not enough farmers to spawn safely this turn; skip spawning
            return

        # Step 3: Spawning planning based on current wheat
        total_wheat = int(getattr(environment.farm, "wheat", 0))

        # Farmers available for spawning (these are in village)
        available_farmers = list(farmers_in_village)

        # Reserve at least MIN_VILLAGE_FARMERS to stay in village
        max_spawning_pool = max(0, len(available_farmers) - MIN_VILLAGE_FARMERS)

        # Spawn Farmer first: needs 2 farmers and 10 wheat per spawn
        max_spawn_farmer = min(max_spawning_pool // 2, total_wheat // 10)
        spawn_farmer_count = 2 * max_spawn_farmer

        # Assign 2*max_spawn_farmer farmers to "spawn farmer"
        for i in range(spawn_farmer_count):
            comp = available_farmers[i]
            self.environment.assign_group(comp, "spawn farmer")

        # Wheat remaining after spawning farmers
        wheat_after_farmer_spawns = total_wheat - (10 * max_spawn_farmer)

        # Remaining farmers after allocating to spawn farmers
        remaining_after_farmer_spawns = available_farmers[spawn_farmer_count:]

        # Spawn Warrior: needs 2 farmers and 12 wheat per spawn
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