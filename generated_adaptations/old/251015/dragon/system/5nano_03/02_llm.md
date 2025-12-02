Reasoning and strategy:
- Constraints: Warriors must go to the Cave to attack the Dragon; Farmers stay in the Village to farm or spawn new villagers. Spawning requires both donors (two villagers assigned to a spawn group) and wheat (10 for a Farmer, 12 for a Warrior).
- Primary goal: Kill the Dragon quickly while maintaining growth. Immediate DPS comes from Warriors in the Cave; long-term wheat/villager production comes from Farmers in the Village.
- Adaptation plan:
  - In assign_in_village:
    - Send all Warriors to the Cave (group "cave").
    - For Farmers, use a two-tier spawning plan to grow the village when wheat allows:
      - Determine how many "spawn farmer" events can occur: spawns_f = min(F // 2, wheat // 10), where F is the number of Farmers in the Village.
      - Use 2*spawns_f Farmers designated to the "spawn farmer" group to trigger those spawns.
      - With remaining Farmers, and the remaining wheat after using 10 per Farmer spawn, compute spawns_w for warriors spawning: spawns_w = min((F - 2*spawns_f) // 2, (wheat - 10*spawns_f) // 12).
      - Assign 2*spawns_w Farmers to the "spawn warrior" group to trigger Warrior spawns.
      - The rest of Farmers go to the "farm" group to continue producing wheat.
  - In assign_in_cave:
    - All Warriors in the Cave go to the "attack" group to actively fight the Dragon.
    - Any other villagers in the Cave (if any) go back to the Village (group "village") to resume farming/spawn planning.
- This strategy ensures:
  - Immediate Dragon pressure from Warriors.
  - Continuous growth of the village when wheat allows, via spawning both Farmers and Warriors.
  - Farmers remain in the Village to farm and provide wheat for spawning.

Python code (SmartAdaptation class):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by current role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Wheat available for spawning
        wheat = 0
        farm = getattr(environment, 'farm', None)
        if farm is not None:
            wheat = getattr(farm, 'wheat', 0)

        F = len(farmers)

        # Determine possible spawns:
        spawns_f = min(F // 2, wheat // 10)  # number of new Farmers to spawn
        wheat_remaining = wheat - spawns_f * 10

        spawns_w = min((F - 2 * spawns_f) // 2, wheat_remaining // 12)  # number of new Warriors to spawn

        # Assign 2*spawns_f farmers to "spawn farmer"
        idx = 0
        for _ in range(2 * spawns_f):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], 'spawn farmer')
                idx += 1

        # Assign 2*spawns_w farmers to "spawn warrior"
        for _ in range(2 * spawns_w):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], 'spawn warrior')
                idx += 1

        # Remaining farmers go to "farm"
        for i in range(idx, len(farmers)):
            environment.assign_group(farmers[i], 'farm')

        # All Warriors go to the Cave (to be in Cave by next step)
        for w in warriors:
            environment.assign_group(w, 'cave')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, send Warriors to attack; send others back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')
```