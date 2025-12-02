Reasoning and updated strategy:
- Why the previous approach underperformed
  - The earlier logic limited spawning too aggressively or too conservatively, and in some cases left no farmers to farm for wheat growth. That reduces the ability to sustain further spawns and reduces early DPS gains from Warriors.
  - The key to a faster kill is to get as many Warriors to the Cave as early as possible while still maintaining enough wheat production to spawn additional villagers over time.

- New greedy but robust approach
  - In assign_in_village:
    - Do not prematurely lock a fixed number of farmers to farming. Instead, compute the maximum number of spawns (Warrior spawns first, then Farmer spawns) based on current wheat and the number of Farmers.
    - Spawns require 2 villagers each; Warriors are more valuable, so prioritize Warrior spawns first.
    - After computing spawns, assign:
      - The 2*S_war farmers to "spawn warrior" (to spawn S_war Warriors).
      - The 2*S_far farmers to "spawn farmer" (to spawn S_far Farmers).
      - The remaining farmers to "farm".
    - Finally, assign all existing Warriors to "cave" (they will attack the Dragon).
  - In assign_in_cave:
    - All Warriors go to the "attack" group.
    - All Farmers go to the "village" group (to continue farming or spawning in the next village step).
  - A safeguard: if all farmers would be used for spawning in a step (2*(S_war+S_far) == F), gracefully reduce spawning so at least some farmers can farm. This ensures wheat production continues for future turns.

- Benefits
  - More Warriors reach the Cave earlier, increasing DPS sooner.
  - Wheat production is kept sustainable by ensuring some farmers are always farming unless spawning is strictly impossible.

Python implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)
        # If no farmers, nothing to spawn; all Warriors go to cave
        if F == 0:
            for w in warriors:
                environment.assign_group(w, "cave")
            return

        # Wheat available for spawning
        W = getattr(environment.farm, "wheat", 0)

        # Compute max possible Warrior spawns first
        # Each Warrior spawn consumes 2 farmers and 12 wheat
        max_war_spawns = min(F // 2, W // 12)

        # Remaining farmers after Warrior spawns
        remaining_after_war = F - 2 * max_war_spawns
        W_after_war = W - 12 * max_war_spawns

        # Compute max possible Farmer spawns after Warrior spawns
        max_far_spawns = min(remaining_after_war // 2, W_after_war // 10)

        # Safe-guard: do not consume all farmers if possible; try to keep some farming
        if 2 * (max_war_spawns + max_far_spawns) == F:
            # If we can reduce one spawn, do so to leave at least some farming
            if max_far_spawns > 0:
                max_far_spawns -= 1
            elif max_war_spawns > 0:
                max_war_spawns -= 1

        # Assign Farmers according to spawning plan
        idx = 0
        #  - Warrior spawns: 2 * max_war_spawns farmers
        for _ in range(2 * max_war_spawns):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        #  - Farmer spawns: 2 * max_far_spawns farmers
        for _ in range(2 * max_far_spawns):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        #  - Remaining farmers go to farming
        while idx < F:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # Finally, assign Warriors to cave (they will attack in the cave step)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers go to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fall back: keep in cave
                environment.assign_group(c, "cave")
```