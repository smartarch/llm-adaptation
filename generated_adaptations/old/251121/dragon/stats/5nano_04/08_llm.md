Reasoning and updated adaptation strategy:
- Goal recap: Kill the Dragon as fast as possible while keeping villagers alive and maintaining wheat production to enable spawning.
- What improved:
  - Maintain a solid wheat-producing core in the Village by reserving a small number of Farmers for farming every step (so wheat can accumulate).
  - Spawn potential new Warriors first, using wheat efficiently (12 wheat for a Warrior pair) and only if there are at least 2 free Farmers in the pool.
  - If there is still wheat after Warrior spawning, spawn a pair of Farmers (10 wheat) to grow future DPS, but avoid overloading the Cave with attackers too quickly.
  - In the Cave, keep all Warriors attacking; send Farmers back to Village to avoid unnecessary casualty risk in the Cave.
- Expected benefits:
  - Steady DPS ramp via Warriors while preserving a reliable wheat supply for ongoing spawns.
  - Bounded per-step spawning to reduce catastrophic losses from dragon attacks.
  - Simpler, more predictable behavior that should improve win chances within 30 steps.

Code (Python):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) != 'Farmer']

        # 1) All Warriors go to the Cave to attack
        for c in warriors:
            environment.assign_group(c, 'cave')

        # 2) Village actions for Farmers
        F = len(farmers)

        # Reserve up to 4 farmers for farming to keep wheat flowing
        reserved_for_farm = min(4, F)

        # Remaining farmers available for spawning decisions
        remaining = farmers[reserved_for_farm:]

        # Wheat available in the Farm
        wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, 'wheat', 0)

        i = 0
        # Spawn at most one Warrior pair if possible (12 wheat)
        if i + 1 < len(remaining) and wheat >= 12:
            a = remaining[i]
            b = remaining[i + 1]
            environment.assign_group(a, 'spawn warrior')
            environment.assign_group(b, 'spawn warrior')
            wheat -= 12
            i += 2

        # If possible, spawn one Farmer pair with remaining wheat (10 wheat)
        if i + 1 < len(remaining) and wheat >= 10:
            a = remaining[i]
            b = remaining[i + 1]
            environment.assign_group(a, 'spawn farmer')
            environment.assign_group(b, 'spawn farmer')
            wheat -= 10
            i += 2

        # Any leftover farmers go to farming
        while i < len(remaining):
            environment.assign_group(remaining[i], 'farm')
            i += 1

        # Ensure reserved farming farmers are set to farming
        for idx in range(reserved_for_farm):
            environment.assign_group(farmers[idx], 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors attack; Farmers should go back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')
```