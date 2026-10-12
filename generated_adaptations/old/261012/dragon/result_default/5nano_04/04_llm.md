Reasoning and improved adaptation strategy

- What we changed
  - We moved from a simple greedy split to a dynamic, wheat-aware spawning plan that prioritizes early Warrior spawns to boost DPS, then uses remaining farmers to spawn additional Villagers, all while preserving a Wheat production pipeline.
  - The strategy continues to follow the rule: all Warriors go to the Cave to attack the Dragon, and Farmers stay in the Village to farm and/or spawn. Spawning uses the two-villager + required wheat rule, and spawners are allocated in a way that respects current wheat in the Farm.
  - In the Cave, we continue to keep Warriors in the attack group and send Farmers back to the Village, minimizing unnecessary exposure of farmers to Dragon counterattacks.

- Why this could win faster
  - Early DPS is crucial to kill the Dragon within 30 steps. By prioritizing Warrior spawns (needs 2 Farmers and 12 wheat) we increase the number of attackers quickly, accelerating Dragon HP reduction.
  - After maximizing Warrior spawns given wheat, we use remaining Farmers to spawn more Villagers (needs 2 Farmers and 10 wheat), which gradually increases overall capacity to sustain farming and potential future spawns.
  - Leaving the non-spawning Farmers in Farm or Farm-related tasks ensures Wheat production remains steady, enabling future spawns and maintaining a pipeline toward a faster kill.

- How the plan works per method
  - assign_in_village:
    - Move all Warriors to the cave (as required).
    - With the list of Farmers still in the Village, first compute how many Warrior spawns are possible given 12 wheat per spawn and 2 Farmers per spawn.
    - Allocate 2 Farmers to each “spawn warrior” group until wheat or farmer count blocks further spawns.
    - With any remaining Farmers and wheat, allocate 2 Farmers per “spawn farmer” group.
    - Any leftover Farmers stay in the Village and are assigned to the “farm” group to keep Wheat production alive.
  - assign_in_cave:
    - All Warriors go to “attack” in the Cave.
    - Farmers in the Cave are sent to the Village.

- This approach should help increase early DPS while maintaining wheat momentum for sustained spawns, potentially reducing the number of turns to kill the Dragon.

Python implementation

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

        # Handle Farmers: dynamic spawning prioritizing Warriors first
        if not farmers:
            return

        available_wheat = getattr(environment.farm, 'wheat', 0)
        num_farmers = len(farmers)
        idx = 0

        # First, spawn as many Warriors as possible (needs 2 farmers and 12 wheat per Warrior)
        max_warrior_spawns = min(num_farmers // 2, available_wheat // 12)

        for _ in range(max_warrior_spawns):
            environment.assign_group(farmers[idx], 'spawn warrior')
            environment.assign_group(farmers[idx + 1], 'spawn warrior')
            idx += 2

        remaining_farmers = num_farmers - idx
        remaining_wheat = available_wheat - max_warrior_spawns * 12

        # Then spawn Farmers if possible (needs 2 farmers and 10 wheat per Farmer)
        max_farmer_spawns = min(remaining_farmers // 2, remaining_wheat // 10)

        for _ in range(max_farmer_spawns):
            environment.assign_group(farmers[idx], 'spawn farmer')
            environment.assign_group(farmers[idx + 1], 'spawn farmer')
            idx += 2

        # Remaining farmers go to farming in Village
        for j in range(idx, num_farmers):
            environment.assign_group(farmers[j], 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Attack with Warriors; Farmers should go to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')
```