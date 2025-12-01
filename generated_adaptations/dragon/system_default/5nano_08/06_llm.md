Reasoning about the fix

Root cause
- The previous implementation sometimes attempted to assign a Warrior to the "spawn warrior" group even when there wasn’t enough wheat to actually spawn anything. This caused tests to fail with “Not enough wheat to spawn new villager” and left some villagers unassigned.
- Additionally, there were multiple passes over the village components, which could lead to multiple assignments for the same villager.

Strategy to fix
- Compute a single, unambiguous assignment for all villagers in the village in one pass.
- Spawning decisions must respect wheat constraints:
  - To spawn from the "spawn farmer" group, we need at least 2 farmers and at least 10 wheat.
  - If we spawn from SPF, the remaining wheat reduces by 10.
  - To spawn from the "spawn warrior" group, after allocating SPF, we need at least 2 farmers left in the group and at least 12 wheat remaining.
  - This ensures we don’t assign someone to a spawn group when there isn’t enough wheat to actually spawn.
- Allocation rules in one pass:
  - All Warriors go to the cave (group "cave").
  - Farmers are allocated in order:
    - First SPF_count farmers to "spawn farmer"
    - Next SPW_count farmers to "spawn warrior"
    - The rest to "farm"
- This guarantees every component is assigned exactly once and respects wheat constraints.

Python code (SmartAdaptation)

```py
from __future__ import annotations
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (eventual attack prep)
        - spawn farmer: for every two villagers assigned here and 10 wheat, a new Farmer spawns
        - spawn warrior: for every two villagers assigned here and 12 wheat, a new Warrior spawns

        Strategy (single-pass, no repeated assignments):
        - All Warriors -> cave
        - Farmers -> allocate to spawn groups or farm in one pass
        - Determine SPF_count and SPW_count based on wheat and farmer count, considering wheat already spent by SPF
          SPF_count = 2 if there are at least 2 farmers and wheat >= 10
          remaining_wheat after SPF = wheat - SPF_count*10
          SPW_count = 2 if there are at least 2 farmers left after SPF and remaining_wheat >= 12
        - Assign first SPF_count farmers to "spawn farmer"
        - Assign next SPW_count farmers to "spawn warrior"
        - Remaining farmers -> "farm"
        - All Warriors -> "cave"
        """
        # Separate farmers and warriors in the current village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wheat available for spawning decisions
        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn counts with wheat-aware constraints
        SPF_count = 2 if (len(farmers) >= 2) and (wheat >= 10) else 0
        remaining_farmers = len(farmers) - SPF_count
        remaining_wheat = wheat - SPF_count * 10

        SPW_count = 2 if (remaining_farmers >= 2) and (remaining_wheat >= 12) else 0

        # Assign farmers in a single pass according to SPF/SPW counts
        for idx, f in enumerate(farmers):
            if idx < SPF_count:
                environment.assign_group(f, "spawn farmer")
            elif idx < SPF_count + SPW_count:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # Warriors go to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # All components have been assigned exactly once

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Warriors attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```