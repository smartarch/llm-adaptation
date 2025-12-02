Reasoning and updated strategy

What went wrong previously
- The earlier approach assigned the same component to multiple groups within a single call (e.g., both to "farm" and later to "spawn farmer"), causing repeated assignments.
- We need a single, explicit assignment per component per method call.
- Spawn decisions must be made in a way that guarantees at least some spawning when possible, while preserving the requirement that all Warriors end up in the Cave and all Farmers stay in the Village. Spawning should be done deterministically by selecting specific villagers to the "spawn" groups, so no component is assigned more than once.

Updated strategy
- Build a single assignment plan per call:
  - Default: Farmers -> farm, Warriors -> cave (these reflect the “farm” and “cave” goals).
  - Then optionally designate up to two Farmers to the "spawn farmer" group if there are at least two Farmers and the Farm has at least 10 wheat.
  - Then designate up to two additional villagers (not already assigned to "spawn farmer") to the "spawn warrior" group if there are at least two such candidates and the Farm has at least 12 wheat.
- After deciding the plan, assign every component exactly once according to that plan.
- In assign_in_cave, keep the simple rule: Warriors go to attack the Dragon, Farmers go to village, any others stay in cave. This ensures all Warriors attack, and Farmers stay in Village as required.

This approach ensures:
- No component is assigned to more than one group in a single step.
- Spawn opportunities are exploited when possible.
- Warriors end up in the Cave and attack; Farmers stay in Village.
- Early attack pressure is supported by having Warriors in the Cave and potentially spawning new units.

Python code

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Build a single, explicit plan: component -> target_group
        plan = {}

        # Classify villagers
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default assignments: Farmers->farm, Warriors->cave
        for c in components:
            role = getattr(c, "role", None)
            if role == "Farmer":
                plan[c] = "farm"
            elif role == "Warrior":
                plan[c] = "cave"
            else:
                # Fallback if role is unknown
                plan[c] = "farm"

        # Attempt to spawn a new Farmer: need 2 villagers in "spawn farmer" and 10 wheat
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            a, b = farmers[0], farmers[1]
            plan[a] = "spawn farmer"
            plan[b] = "spawn farmer"

        # Attempt to spawn a new Warrior: need 2 villagers in "spawn warrior" and 12 wheat
        # Exclude those already allocated to "spawn farmer"
        candidates = [c for c in components if plan.get(c) != "spawn farmer"]
        if len(candidates) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            c1, c2 = candidates[0], candidates[1]
            plan[c1] = "spawn warrior"
            plan[c2] = "spawn warrior"

        # Apply the plan: assign each component exactly once
        for c, target in plan.items():
            environment.assign_group(c, target)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack the Dragon; Farmers go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback for unknown roles
                environment.assign_group(c, "cave")
```