Strategy reasoning

Goal and constraints recap
- All Warriors must end up in the Cave and attack the Dragon.
- All Farmers must stay in the Village (they can farm or participate in spawning).
- Spawn mechanics should be used when possible:
  - Spawn Farmer: at least two villagers assigned to the spawn farmer group and at least 10 wheat.
  - Spawn Warrior: after allocating potential spawn farmer, at least two villagers (not already spawning a farmer) and at least 12 wheat.
- The Dragon should be attacked, with at least one attack in the first 15 steps.
- We must ensure every component (villager) is assigned to exactly one group in a given assign_in_village call.

What to fix
- The tests were failing because some villagers could be left unassigned in edge cases. To guarantee every villager is assigned exactly once in assign_in_village, we switch to a deterministic, identity-based membership approach.

Key idea
- Build two exclusive sets for spawning:
  - spawn_farmer_set: two Farmers if there are at least two Farmers and at least 10 wheat.
  - spawn_war_set: two other villagers (not in spawn_farmer_set) if there are at least two and at least 12 wheat.
- For each villager, choose its target in this priority:
  - If in spawn_farmer_set -> spawn farmer
  - Else if in spawn_war_set -> spawn warrior
  - Else assign by role: Farmer -> farm, Warrior -> cave, Unknown -> farm
- This guarantees every villager gets exactly one assignment in a single pass and handles edge cases like no initial warriors or all farmers.

Python code

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Identify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Determine spawning opportunities deterministically
        spawn_farmer_set = set()
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            spawn_farmer_set.update([farmers[0], farmers[1]])

        spawn_war_set = set()
        # Exclude those already chosen for spawning a farmer
        candidates_for_war = [c for c in components if c not in spawn_farmer_set]
        if len(candidates_for_war) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            w1, w2 = candidates_for_war[0], candidates_for_war[1]
            spawn_war_set.update([w1, w2])

        # Assign each component exactly once according to the plan
        for c in components:
            if c in spawn_farmer_set:
                environment.assign_group(c, "spawn farmer")
            elif c in spawn_war_set:
                environment.assign_group(c, "spawn warrior")
            else:
                role = getattr(c, "role", None)
                if role == "Farmer":
                    environment.assign_group(c, "farm")
                elif role == "Warrior":
                    environment.assign_group(c, "cave")
                else:
                    # Fallback for unknown roles
                    environment.assign_group(c, "farm")

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