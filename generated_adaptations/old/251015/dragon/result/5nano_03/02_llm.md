Reasoning and adaptation strategy

Goal and constraints
- All Warriors should head to the Cave and then attack the Dragon.
- All Farmers should stay in the Village and either farm or spawn new villagers (Farmers and Warriors are both needed for spawning to occur).
- Spawning mechanics: 
  - "spawn farmer": for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
  - "spawn warrior": for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
- We must assign every component to exactly one group for both Village and Cave contexts.
- We can observe wheat via environment.farm.wheat and dragon health via environment.dragon.hp, but the spawning mechanics are handled by the environment once we assign groups.

Strategy
- In assign_in_village:
  - Move all Warriors to the cave (group "cave").
  - For Farmers:
    - If we have at least 2 Farmers and there is at least 10 wheat, designate two Farmers to the "spawn farmer" group to enable spawning; assign the remaining Farmers to "farm".
    - If there are fewer than 2 Farmers, assign all Farmers to "farm" (no spawning possible).
  - Do not use "spawn warrior" unless you want to, keeping the strategy simple and aligned with the rule that Farmers are primarily responsible for spawning. This ensures a steady wheat production and potential spawn of new villagers without overcomplicating the spawning logic.
- In assign_in_cave:
  - All Warriors in the cave go to "attack" to fight the Dragon.
  - All Farmers in the cave go back to the Village ("village"), since Farmers should stay in the Village for farming/spawning.

This approach guarantees the required behavior: Warriors attack, Farmers stay in the Village to farm or trigger spawns, and spawns are attempted when there are enough Farmers and wheat.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in the Village to farm or spawn
        # Use a simple spawning plan:
        # - If we have >= 2 farmers and at least 10 wheat, assign 2 to "spawn farmer" to enable spawning.
        # - The remaining farmers go to "farm".
        # - If we have fewer than 2 farmers, all go to "farm".
        if len(farmers) >= 2:
            # Try to spawn: allocate first two farmers to the spawn group
            spawn_candidates = farmers[:2]
            for f in spawn_candidates:
                environment.assign_group(f, "spawn farmer")
            # Remaining farmers go to farming
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
        else:
            # Not enough farmers to spawn, all farm
            for f in farmers:
                environment.assign_group(f, "farm")

        # Note: We intentionally do not assign anyone to "spawn warrior" to keep the strategy simple.
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors should attack, Farmers should return to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```