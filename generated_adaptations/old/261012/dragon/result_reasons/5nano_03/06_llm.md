Reasoning and strategy improvements:
- Goal alignment remains: all Warriors go to the Cave to attack, Farmers stay in the Village, and we spawn new villagers to boost both DPS (new Warriors) and wheat production (new Farmers).
- Key insight: To kill the Dragon faster, push as much extra DPS as early as possible. Spawn as many Warriors as allowed by current wheat and available farmers, then use any remaining wheat to spawn Farmers so wheat production accelerates for subsequent spawns.
- Greedy, step-agnostic spawning:
  - In assign_in_village, first move all Warriors to the cave so they can attack as soon as possible.
  - Then greedily spawn Warriors: for every two Farmers we commit to "spawn warrior" we need 12 wheat. We allocate as many Warrior spawns as possible given the number of Farmers and the available wheat.
  - Next, with the remaining Farmers and wheat, greedily spawn Farmers: for every two Farmers we commit to "spawn farmer" we need 10 wheat. This increases future wheat production to support more spawns and sustained DPS.
  - All leftover Farmers remain in the Village to farm.
- In assign_in_cave, continue to keep Warriors in attack mode and Farmers in the Village.
- This approach:
  - Ensures early dragon damage by sending all Warriors to cave immediately.
  - Maximizes the number of Warriors spawned in early steps to improve DPS quickly.
  - Builds wheat production to enable more spawns later, supporting faster overall kill times.

Python implementation:
```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors currently in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Strategy: All Warriors should go to the Cave to attack the Dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Greedy spawning logic using current wheat and available farmers
        wheat = int(getattr(environment.farm, "wheat", 0))
        remaining = list(farmers)

        # First, spawn as many Warriors as possible:
        # Each Warrior spawn requires 2 farmers and 12 wheat
        max_warrior_spawns = min(len(remaining) // 2, wheat // 12)
        for _ in range(max_warrior_spawns * 2):
            f = remaining.pop(0)
            environment.assign_group(f, "spawn warrior")
        wheat -= max_warrior_spawns * 12

        # Then, spawn as many Farmers as possible with remaining farmers and wheat
        # Each Farmer spawn requires 2 farmers and 10 wheat
        max_farm_spawns = min(len(remaining) // 2, wheat // 10)
        for _ in range(max_farm_spawns * 2):
            f = remaining.pop(0)
            environment.assign_group(f, "spawn farmer")
        wheat -= max_farm_spawns * 10

        # Remaining farmers stay in the village to farm
        for f in remaining:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: all Warriors attack; Farmers stay in Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```