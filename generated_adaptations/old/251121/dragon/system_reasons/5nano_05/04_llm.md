Strategy update and reasoning:

- Fix the root cause of failures: In the previous version, assign_in_village assigned the same Farmer components to multiple groups within the same step (first to farm, then to spawn groups, etc.). This caused "component assigned more than once" errors. The adaptation must assign every component exactly once per call to assign_in_village.
- Approach to satisfy requirements robustly:
  - In assign_in_village:
    - Keep all Farmers in the Village by default, but decide upfront for each Farmer whether they should join:
      - "farm"
      - "spawn farmer"
      - "spawn warrior"
    - All Warriors must go to the Cave (group "cave") in the village step.
    - Spawning logic is computed in one pass:
      - Compute how many Farmer-spawn events we can perform given current wheat: f_spawns = min(number_of_farmers // 2, wheat // 10)
      - After allocating Farmer-spawns, compute remaining wheat and how many Warrior-spawn events we can perform: w_spawns = min((remaining_farmers) // 2, remaining_wheat // 12)
      - Assign exactly 2*f_spawns Farmers to "spawn farmer", 2*w_spawns Farmers to "spawn warrior", and the remaining Farmers to "farm".
  - In assign_in_cave:
    - For the villagers currently in the Cave, assign Warriors to "attack" and Farmers to "village" (i.e., move Farmers back to Village). This ensures the Dragon is attacked by Warriors and Farmers stay back to farm or spawn in the Village.
  - This keeps every component assigned exactly once per step, prevents repeated assignments, and respects the spawn rules and movement constraints.

Python code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Wheat available for spawning decisions
        wheat = getattr(environment.farm, "wheat", 0)

        # Determine how many farmer-spawns we can perform: need 2 farmers + 10 wheat per spawn
        f_spawns = min(len(farmers) // 2, wheat // 10)

        # Wheat left after farmer-spawns
        wheat_after_f_farm = wheat - f_spawns * 10

        # Remaining farmers after allocating to farmer-spawns
        remaining_farmers_after_f_farm = len(farmers) - (2 * f_spawns)

        # Determine how many warrior-spawns we can perform: need 2 farmers + 12 wheat per spawn
        w_spawns = min(remaining_farmers_after_f_farm // 2, wheat_after_f_farm // 12)

        # Build final assignment for each farmer in a single pass (no repeated assignments)
        idx = 0
        for f in farmers:
            if idx < 2 * f_spawns:
                group = "spawn farmer"
            elif idx < 2 * f_spawns + 2 * w_spawns:
                group = "spawn warrior"
            else:
                group = "farm"
            environment.assign_group(f, group)
            idx += 1

        # All warriors must go to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, attack strategy:
        # Warriors -> attack the Dragon
        # Farmers  -> go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```