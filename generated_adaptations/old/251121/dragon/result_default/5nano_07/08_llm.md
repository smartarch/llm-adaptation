Reasoning and updated strategy:
- Why previous attempts struggled:
  - Spawning policy could deplete all farmers, risking zero wheat production in future turns.
  - Warriors were not guaranteed to reach the Dragon early enough in some scenarios, delaying high DPS.
  - We need a robust, dynamic policy that always pushes Warriors to the Cave while maintaining a minimal farming backbone to sustain wheat for spawning over multiple turns.

- New approach (greedy but sustainable, dynamic with wheat):
  - In assign_in_village:
    - Move all Warriors to the Cave immediately to start dealing DPS sooner.
    - Use Farmers to spawn as many Warriors as possible first, but preserve at least one Farmer for farming if possible (to keep wheat growth ongoing).
    - After Warrior spawns, use any remaining Farmers to spawn Farmers (to grow the population and wheat) if wheat allows.
    - Any leftover Farmers stay farming.
  - In assign_in_cave:
    - All Warriors attack (group "attack").
    - Farmers stay in the Village (group "village") to continue farming or spawning next turn.
  - This approach prioritizes early DPS from Warriors while maintaining a sustainable wheat supply for ongoing growth.

Python implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        F = len(farmers)
        if F == 0:
            # No farmers to produce wheat; nothing more to do this turn
            return

        # Wheat available for spawning
        W = getattr(environment.farm, "wheat", 0)

        # 2) Spawn Warriors first, but preserve at least one Farmer for farming when possible
        # Ensure at least one farmer remains if there are enough farmers
        max_war_spawns = 0
        if F >= 3:
            max_war_spawns = min((F - 1) // 2, W // 12)

        # After Warrior spawns, compute remaining farmers and wheat
        remaining_after_war = F - 2 * max_war_spawns
        W_after_war = W - 12 * max_war_spawns

        # 3) Spawn Farmers with the remaining resources
        max_far_spawns = 0
        if remaining_after_war >= 2 and W_after_war >= 10:
            max_far_spawns = min(remaining_after_war // 2, W_after_war // 10)

        # Assign groups
        idx = 0
        # Warrior spawns: 2 farmers per spawn_war
        for _ in range(2 * max_war_spawns):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Farmer spawns: 2 farmers per spawn_far
        for _ in range(2 * max_far_spawns):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Remaining farmers go to farming
        while idx < F:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers go to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: stay in cave
                environment.assign_group(c, "cave")
```