Reasoning and targeted fix

Root cause
- The failures indicate occasional missing assignments for some villagers (e.g., Mary) when using object-as-dict-key plans. If the dictionary keying or object identity handling misaligns with how the test harness tracks assignment, some components can slip through without an assigned group.

What I changed
- Switch to a robust, index-based planning approach. Instead of using component objects as dictionary keys, we map assignments by the index of each component within the current village list. This avoids any hashing/equality quirks and guarantees every component gets exactly one assignment in a single pass.
- Build a single pass plan:
  - Default: Farmer -> farm, Warrior -> cave, unknown -> farm.
  - If possible, designate the first two Farmers to spawn farmer (spawn farmer) when there are at least 2 farmers and 10 wheat.
  - From the remaining villagers (excluding the two spawn-farmers), designate the first two to spawn warrior if there are at least 2 and 12 wheat.
- Apply the plan in one loop over the components, using the index-based plan.

This approach guarantees:
- Every villager in the village is assigned exactly once.
- Spawn opportunities are exercised deterministically and without risking missing assignments due to object-key issues.
- Warriors end up in the Cave and can attack, Farmers stay in Village unless spawning.

Python code

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Robust, single-pass assignment by index to avoid object-key issues
        n = len(components)
        # Map component object id to its index in the current village listing
        id_to_index = {id(c): i for i, c in enumerate(components)}

        # Classify villagers
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]

        # Build a plan by index: target_group for each component
        plan = ["farm"] * n  # default

        # Initialize defaults based on role
        for i, c in enumerate(components):
            role = getattr(c, "role", None)
            if role == "Farmer":
                plan[i] = "farm"
            elif role == "Warrior":
                plan[i] = "cave"
            else:
                plan[i] = "farm"  # safe fallback

        # Attempt to spawn a farmer: need at least 2 farmers and 10 wheat
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            f1, f2 = farmers[0], farmers[1]
            plan[id_to_index[id(f1)]] = "spawn farmer"
            plan[id_to_index[id(f2)]] = "spawn farmer"

        # Attempt to spawn a warrior: need 2 villagers (not already spawning farmer) and 12 wheat
        spawn_farmer_ids = set()
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            spawn_farmer_ids.update([id(farmers[0]), id(farmers[1])])

        # Build list of candidates not already spawning a farmer
        candidates_for_war = [c for c in components if id(c) not in spawn_farmer_ids]
        if len(candidates_for_war) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            w1, w2 = candidates_for_war[0], candidates_for_war[1]
            plan[id_to_index[id(w1)]] = "spawn warrior"
            plan[id_to_index[id(w2)]] = "spawn warrior"

        # Apply the plan in a single pass
        for i, c in enumerate(components):
            environment.assign_group(c, plan[i])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors should attack; Farmers should go to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "cave")
```