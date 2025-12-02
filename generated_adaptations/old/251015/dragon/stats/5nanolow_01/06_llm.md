Reasoning:
- The bottleneck in the previous approach was not spawning enough villagers early to grow a scalable force, and not guaranteeing rapid conversion of population into attackers. A stronger adaptation is to aggressively maximize spawning early based on current wheat, while still keeping all Warriors in the Cave to attack and all Farmers in the Village to farm.
- Strategy updates:
  - In assign_in_village:
    - Move all Warriors to the Cave (attack group) immediately.
    - Keep Farmers in the Village (farm group) by default.
    - Compute how many spawns we can perform this turn given the current wheat.
    - First allocate as many "spawn farmer" groups as possible (needs 2 farmers and 10 wheat per spawn).
    - With the remaining farmers and remaining wheat, allocate as many "spawn warrior" groups as possible (needs 2 farmers and 12 wheat per spawn).
    - Any farmers not involved in spawning stay in the Village as farmers.
  - In assign_in_cave:
    - All Warriors go to "attack" to maximize damage to the Dragon.
    - Farmers return to the Village ("village") to continue farming/spawning.

- This approach aims to quickly swell the army via spawning, then push sustained damage through Warriors in the Cave, improving the chance to kill the Dragon earlier.

Python code (class SmartAdaptation implementing the strategy):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Step 1: Default assignments
        farmers_in_village = []
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                # Warriors should head to the Cave to attack
                self.environment.assign_group(comp, "cave")
            else:
                # Farmers stay in the Village by default
                farmers_in_village.append(comp)
                self.environment.assign_group(comp, "farm")

        # If no farmers, nothing more to spawn this turn
        if not farmers_in_village:
            return

        # Step 2: Spawning planning based on current wheat
        total_wheat = int(getattr(environment.farm, "wheat", 0))

        available_farmers = list(farmers_in_village)

        # Max possible "spawn farmer" spawns this turn
        max_spawn_farmer = min(len(available_farmers) // 2, total_wheat // 10)
        spawn_farmer_count = 2 * max_spawn_farmer

        # Assign first 2*max to "spawn farmer"
        for i in range(spawn_farmer_count):
            comp = available_farmers[i]
            self.environment.assign_group(comp, "spawn farmer")

        # Wheat remaining after spawning farmers
        wheat_after_farmer_spawns = total_wheat - (10 * max_spawn_farmer)

        # Remaining farmers after allocating to spawn farmers
        remaining_after_farmer_spawns = available_farmers[spawn_farmer_count:]

        # Max possible "spawn warrior" spawns with remaining farmers and wheat
        max_spawn_warrior = min(len(remaining_after_farmer_spawns) // 2, wheat_after_farmer_spawns // 12)
        spawn_warrior_count = 2 * max_spawn_warrior

        # Assign the next 2*max_spawn_warrior farmers to "spawn warrior"
        for i in range(spawn_warrior_count):
            comp = remaining_after_farmer_spawns[i]
            self.environment.assign_group(comp, "spawn warrior")

        # Any leftover farmers remain in their current groups (farm) or can be left as-is

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                self.environment.assign_group(comp, "attack")
            else:
                # Farmers should go back to the village
                self.environment.assign_group(comp, "village")
```