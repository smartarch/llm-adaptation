Strategy update

Goal
- Guarantee that every villager in the village is assigned to exactly one group in each assign_in_village call.
- Use a deterministic single-pass plan that assigns all villagers: some to spawn groups if possible, the rest to their default roles.
- Maintain the constraint that Warriors go to the Cave (and eventually attack) and Farmers stay in the Village (farm or spawn). Spawn opportunities are exercised when wheat allows.

Key changes
- Build an explicit per-call assignment map without relying on multiple passes or id-based plan overwrites.
- Steps:
  - Default: Farmers -> farm, Warriors -> cave, unknown -> farm.
  - If possible, promote two Farmers to spawn farmer (needs at least 2 Farmers and 10 wheat).
  - From the remaining villagers (excluding the two spawn farmers), promote two to spawn warrior if there are at least two and there is at least 12 wheat.
  - Apply the assignment to all components in a single pass.

This approach ensures every component is assigned exactly once, even in edge cases like no initial warriors.

Python code

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Build a robust, single-pass explicit assignment for all villagers
        assignment = {}

        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Default assignments based on role
        for c in components:
            role = getattr(c, "role", None)
            if role == "Farmer":
                assignment[c] = "farm"
            elif role == "Warrior":
                assignment[c] = "cave"
            else:
                assignment[c] = "farm"  # fallback for unknown roles

        # 2) Spawn farmer if possible: 2 villagers in spawn farmer and 10 wheat
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            f1, f2 = farmers[0], farmers[1]
            assignment[f1] = "spawn farmer"
            assignment[f2] = "spawn farmer"

        # 3) Spawn warrior if possible: 2 villagers (not already spawning farmer) and 12 wheat
        remaining_for_war = [c for c in components if assignment.get(c) != "spawn farmer"]
        if len(remaining_for_war) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            w1, w2 = remaining_for_war[0], remaining_for_war[1]
            assignment[w1] = "spawn warrior"
            assignment[w2] = "spawn warrior"

        # 4) Apply the assignment in a single pass
        for c in components:
            target = assignment.get(c, "farm")
            environment.assign_group(c, target)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack; Farmers stay in Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "cave")
```