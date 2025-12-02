Reasoning and new adaptation strategy:
- Why previous attempts failed: The Dragon’s HP is high (50). Warriors deal 3 damage but dying villagers in the Cave can wipe out an entire wave quickly due to dragon retaliation. Wheat is the bottleneck for spawning, so a steady wheat engine plus a cautious DPS ramp is needed. Overly aggressive spawning increases casualties; too little spawning delays DPS ramp and dragon kill time.
- New approach (safer, steadier ramp):
  - Keep a small, steady wheat-producing core in the Village by reserving a fixed number of Farmers for farming every step (to guarantee ongoing wheat).
  - Spawn at most one Warrior pair per step if there is enough wheat and at least two free Farmers to spare.
  - After spawning a Warrior pair, optionally spawn at most one Farmer pair, but only in the earlier phase of the run to avoid starving wheat; otherwise keep farmers farming.
  - All Warriors go to the Cave; Farmers that appear in the Cave are sent back to the Village to minimize risk.
  - This yields a gradual DPS ramp with a consistent wheat engine, reducing catastrophic losses while still pushing toward the Dragon’s death within 30 steps.

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

        # 1) Move Warriors to the Cave (one wave per step to limit casualties)
        if len(warriors) > 0:
            environment.assign_group(warriors[0], 'cave')

        # 2) Village actions for Farmers
        F = len(farmers)
        # Keep a small farming core to sustain wheat production
        reserved_for_farm = min(3, F)

        # Remaining farmers available for spawning decisions
        remaining = farmers[reserved_for_farm:]

        # Wheat available in the Farm
        wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, 'wheat', 0)

        i = 0
        # Spawn at most one Warrior pair per step (12 wheat) if possible
        max_warrior_spawns = 1 if (wheat >= 12) and (len(remaining) >= 2) else 0
        spawned_warrior_pairs = 0
        while spawned_warrior_pairs < max_warrior_spawns and i + 1 < len(remaining) and wheat >= 12:
            a = remaining[i]
            b = remaining[i + 1]
            environment.assign_group(a, 'spawn warrior')
            environment.assign_group(b, 'spawn warrior')
            wheat -= 12
            i += 2
            spawned_warrior_pairs += 1

        # Spawn at most one Farmer pair per step (10 wheat) if possible, after Warrior spawning opportunities
        max_farmer_spawns = 1 if (step < 25) and (wheat >= 10) and (i + 1 < len(remaining)) else 0
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