Strategy reasoning

Goal and constraints recap
- All Warriors must end up in the Cave and attack the Dragon.
- All Farmers must stay in the Village (they can farm or participate in spawning).
- Spawn mechanics should be used when possible:
  - Spawn Farmer: at least two villagers assigned to the spawn farmer group and at least 10 wheat.
  - Spawn Warrior: after allocating potential spawn farmer, at least two villagers (not already spawning a farmer) and at least 12 wheat.
- The Dragon should be attacked, with at least one attack in the first 15 steps.
- We must ensure every component (villager) is assigned to exactly one group in a given assign_in_village call.

Robust approach
- Build a single, explicit plan per assign_in_village call, mapping each villager to exactly one target group.
- Start with a default mapping based on role:
  - Farmer -> farm
  - Warrior -> cave
  - Unknown role -> farm (safe fallback)
- Then deterministically designate up to two Farmers to spawn Farmer if there are at least two Farmers and 10 wheat.
- From the remaining villagers (excluding those designated for spawn farmer), deterministically designate up to two to spawn Warrior if there are at least two and 12 wheat.
- Finally, apply the plan in one pass, assigning each villager exactly once.
- assign_in_cave remains straightforward: Warriors to attack, Farmers to village, unknowns to cave.

This approach guarantees:
- Every component gets exactly one assignment in assign_in_village.
- Spawn opportunities are leveraged deterministically.
- Warriors end up in the Cave and attack; Farmers stay in Village.
- Edge cases like no initial Warriors (only Farmers) are handled cleanly.

Python code

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Build a robust, single-pass plan: map each component to exactly one target group.
        plan = {}

        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default assignments based on role
        for c in components:
            role = getattr(c, "role", None)
            if role == "Farmer":
                plan[c] = "farm"
            elif role == "Warrior":
                plan[c] = "cave"
            else:
                plan[c] = "farm"  # safe fallback for unknown roles

        # Spawn farmer if possible: need 2 villagers in spawn farmer and 10 wheat
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            f1, f2 = farmers[0], farmers[1]
            plan[f1] = "spawn farmer"
            plan[f2] = "spawn farmer"

        # Spawn warrior if possible: need 2 villagers in spawn warrior and 12 wheat
        # Exclude those already designated for spawn farmer
        candidates = [c for c in components if plan.get(c) != "spawn farmer"]
        if len(candidates) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            w1, w2 = candidates[0], candidates[1]
            plan[w1] = "spawn warrior"
            plan[w2] = "spawn warrior"

        # Apply the plan: assign each component exactly once
        for c in components:
            environment.assign_group(c, plan[c])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack; Farmers go to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "cave")
```