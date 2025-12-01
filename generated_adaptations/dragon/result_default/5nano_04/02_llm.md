Reasoning and adaptation strategy

- Task analysis:
  - Warriors must always go to the Cave and attack the Dragon. Farmers should stay in the Village and focus on farming or spawning new villagers to replenish or grow the workforce.
  - Spawning rules: For every two villagers assigned to a spawn group and the required amount of wheat, a new villager is spawned. Specifically:
    - spawn farmer: needs 2 villagers and 10 wheat per new Farmer.
    - spawn warrior: needs 2 villagers and 12 wheat per new Warrior.
  - The Dragon can harm villagers in the Cave, so we should minimize time spent with large numbers of Farmers in the Cave. The optimal strategy is to keep Warriors in the Cave to maximize DPS while keeping a healthy, wheat-producing Farm base in the Village to sustain spawning.

- Adaptation strategy:
  - assign_in_village:
    - Move all Warriors to the Cave (group "cave") so they can start attacking the Dragon.
    - Manage Farmers in the Village to create a sustainable Wheat flow and to spawn new villagers as needed:
      - Compute how many spawns are possible given current wheat and number of Farmers.
      - Prefer spawning as soon as wheat allows, distributing Farmers between:
        - "spawn farmer" (to increase Farmer numbers) and
        - "spawn warrior" (to increase Warrior numbers).
      - Any Farmers not allocated to spawn groups will stay in the Village and be assigned to "farm" to produce more wheat.
  - assign_in_cave:
    - Re-assign villagers in the Cave so that all Warriors go to "attack" and all Farmers go to "village" (to return to farming or spawn as needed). This ensures farmers do not linger unnecessarily in the Cave.

- Rationale:
  - This approach guarantees maximum immediate DPS by concentrating Warriors in the Cave and feeding a Wheat-generating pipeline via Farmers in the Village.
  - Spawning is driven by available Wheat, with a simple, deterministic distribution that avoids starving the Wheat farm while still enabling growth of the population.
  - If Wheat is scarce, farming is prioritized to accumulate more Wheat for future spawns; if Wheat is abundant, we spawn more Villagers to accelerate DPS growth.

Now the Python implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Divide villagers in the Village into: farm, cave, spawn farmer, spawn warrior
        # Warriors go to cave
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']

        for w in warriors:
            environment.assign_group(w, 'cave')

        # Handle Farmers: decide spawning vs farming
        if farmers:
            # Current wheat available at the Farm
            available_wheat = getattr(environment.farm, 'wheat', 0)
            num_farmers = len(farmers)

            # Plan spawns: each spawn event consumes 2 farmers and some wheat
            spawn_farmers_count = min(num_farmers // 2, available_wheat // 10)

            remaining_farmers_after_farmspawn = num_farmers - spawn_farmers_count * 2
            remaining_wheat_after_farmspawn = available_wheat - spawn_farmers_count * 10

            spawn_warriors_count = min(remaining_farmers_after_farmspawn // 2,
                                       remaining_wheat_after_farmspawn // 12)

            idx = 0
            # Assign to spawn farmer group
            for _ in range(spawn_farmers_count):
                environment.assign_group(farmers[idx], 'spawn farmer')
                environment.assign_group(farmers[idx + 1], 'spawn farmer')
                idx += 2

            # Assign to spawn warrior group
            for _ in range(spawn_warriors_count):
                environment.assign_group(farmers[idx], 'spawn warrior')
                environment.assign_group(farmers[idx + 1], 'spawn warrior')
                idx += 2

            # Remaining farmers go to farming in the Village
            for j in range(idx, num_farmers):
                environment.assign_group(farmers[j], 'farm')
        # If there are no farmers, Warriors have already been sent to cave above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack, Farmers go back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')
```