Reasoning and new adaptation strategy:
- Observations from repeated runs show that large, fast waves of Warriors entering the Cave cause high casualties due to dragon retaliation, and wheat production remains a bottleneck for spawning. A safer, steadier ramp is needed.
- Core ideas for improvement:
  - Limit how many Warriors can be in the Cave at any given time by moving them to the Cave at a controlled rate (e.g., one Warrior at a time per step). This reduces per-step casualties from dragon retaliation.
  - Maintain a small, reliable wheat-producing core in the Village by reserving a fixed number of Farmers for farming each step (to keep wheat flowing).
  - Spawn at most one Warrior pair per step if there is enough wheat and at least two spare Farmers; after that, spawn at most one Farmer pair per step (and only early in the run) to grow future DPS without starving the wheat engine.
  - In the Cave, Warriors attack; Farmers in the Cave are returned to the Village to minimize casualties.
- Expected benefit: a safer, gradual DPS ramp with a stable wheat engine, reducing catastrophic losses and increasing the chance to kill the Dragon within 30 steps.

Code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) != 'Farmer']

        # 1) Move at most one Warrior to the Cave per step to limit casualties
        if len(warriors) > 0:
            environment.assign_group(warriors[0], 'cave')

        # 2) Village actions for Farmers
        F = len(farmers)
        # Keep a small farming core to sustain wheat production
        reserved_for_farm = min(4, F)

        # Remaining farmers available for spawning decisions
        remaining = farmers[reserved_for_farm:]

        # Wheat available in the Farm
        wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, 'wheat', 0)

        i = 0
        # Spawn at most one Warrior pair per step if possible
        max_warrior_spawns = 1 if (len(remaining) >= 2) and (wheat >= 12) else 0
        spawned_warrior_pairs = 0
        while spawned_warrior_pairs < max_warrior_spawns and i + 1 < len(remaining) and wheat >= 12:
            a = remaining[i]
            b = remaining[i + 1]
            environment.assign_group(a, 'spawn warrior')
            environment.assign_group(b, 'spawn warrior')
            wheat -= 12
            i += 2
            spawned_warrior_pairs += 1

        # Spawn at most one Farmer pair per step if possible, after Warrior spawning opportunities
        max_farmer_spawns = 1 if (step < 28) and (i + 1 < len(remaining)) and (wheat >= 10) else 0
        spawned_farmer_pairs = 0
        while spawned_farmer_pairs < max_farmer_spawns and i + 1 < len(remaining) and wheat >= 10:
            a = remaining[i]
            b = remaining[i + 1]
            environment.assign_group(a, 'spawn farmer')
            environment.assign_group(b, 'spawn farmer')
            wheat -= 10
            i += 2
            spawned_farmer_pairs += 1

        # Any leftover farmers go to farming
        while i < len(remaining):
            environment.assign_group(remaining[i], 'farm')
            i += 1

        # Ensure reserved farming farmers are farming
        for idx in range(reserved_for_farm):
            environment.assign_group(farmers[idx], 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors attack; Farmers return to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')
```