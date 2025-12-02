Reasoning and strategy:
- Primary goal is to maximize damage to the Dragon as quickly as possible. Warriors deal more damage and should be the core attack force, so they should ultimately end up in the Cave to attack the Dragon. Farmers should stay in the Village to farm wheat and enable spawning of new villagers, which helps scale the army over time.
- Spawning rules require both population and wheat:
  - spawn farmer: for every two villagers assigned to this group and 10 wheat, one new Farmer is spawned.
  - spawn warrior: for every two villagers assigned to this group and 12 wheat, one new Warrior is spawned.
- To improve performance, allocate villagers to spawn groups greedily based on current wheat and available farmers:
  1) Move all Warriors to the Cave (attack group) and keep Farmers in the Village (farm by default).
  2) In the Village, use Farmers to form spawn groups as wheat allows:
     - First form as many "spawn farmer" groups as possible: needs 2 farmers per spawn and 10 wheat per spawn.
     - With remaining farmers and wheat, form as many "spawn warrior" groups as possible: needs 2 farmers per spawn and 12 wheat per spawn.
  3) In the Cave, send Warriors to "attack" and send Farmers back to "village" to farm or spawn.
- This approach ensures early aggressive pressure from Warriors while growing the population through spawning to sustain longer campaigns.

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

        # If there are no farmers, nothing more to spawn; exit early
        if not farmers_in_village:
            return

        # Step 2: Spawning planning based on current wheat
        # Current wheat in the Farm
        total_wheat = int(getattr(environment.farm, "wheat", 0))

        # Number of farmers available for spawning (all in village by default)
        available_farmers = list(farmers_in_village)

        # Max possible "spawn farmer" spawns
        max_spawn_farmer = min(len(available_farmers) // 2, total_wheat // 10)
        spawn_farmer_count = 2 * max_spawn_farmer

        # Assign the first 2*max to "spawn farmer"
        for i in range(spawn_farmer_count):
            comp = available_farmers[i]
            self.environment.assign_group(comp, "spawn farmer")

        # Update remaining wheat after spawning farmers
        wheat_after_farmer_spawns = total_wheat - (10 * max_spawn_farmer)

        # Remaining farmers after assigning to spawn farmers
        remaining_after_farmer_spawns = available_farmers[spawn_farmer_count:]

        # Max possible "spawn warrior" spawns from the remaining farmers
        max_spawn_warrior = min(len(remaining_after_farmer_spawns) // 2, wheat_after_farmer_spawns // 12)
        spawn_warrior_count = 2 * max_spawn_warrior

        # Assign the next 2*max_spawn_warrior farmers to "spawn warrior"
        for i in range(spawn_warrior_count):
            comp = remaining_after_farmer_spawns[i]
            self.environment.assign_group(comp, "spawn warrior")

        # Any leftovers stay in their current groups (farm) or can be left as-is.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                self.environment.assign_group(comp, "attack")
            else:
                # Farmers should go back to the village
                self.environment.assign_group(comp, "village")
```