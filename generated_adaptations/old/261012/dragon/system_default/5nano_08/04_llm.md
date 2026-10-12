Reasoning about the fix
- The failure indicates some villagers were assigned to more than one group within assign_in_village. The root cause was performing multiple passes and re-assigning the same components.
- To fix, compute a single, unambiguous assignment for every villager in the village and assign each exactly once.
- Strategy adjustments:
  - Creatively categorize Farmers and Warriors in one pass:
    - Warriors go to the cave (group "cave").
    - Farmers mostly stay in the village (group "farm"), but a subset can be allocated to spawn groups.
  - Determine spawn allocations (spawn farmer and spawn warrior) based on current wheat and number of Farmers:
    - SPF_count = 2 if there are at least 2 farmers and wheat >= 10, else 0.
    - SPW_count = 2 if after SPF_count there are at least 2 farmers left and wheat >= 12, else 0.
  - Assign farmers in a single pass:
    - First SPF_count farmers -> "spawn farmer"
    - Next SPW_count farmers -> "spawn warrior"
    - Remaining farmers -> "farm"
  - Warriors: all to "cave".
  - This ensures every component is assigned exactly once.

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
        - Determine SPF_count and SPW_count based on wheat and farmer count
        - Assign first SPF_count farmers to "spawn farmer"
        - Assign next SPW_count farmers to "spawn warrior"
        - Remaining farmers -> "farm"
        """
        # Separate farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wheat available for spawning decisions
        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn counts (per simple policy used here)
        SPF_count = 2 if (len(farmers) >= 2) and (wheat >= 10) else 0
        remaining_after_spf = len(farmers) - SPF_count
        SPW_count = 2 if (remaining_after_spf >= 2) and (wheat >= 12) else 0

        # Assign farmers in a single pass
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

        # No explicit return; all components have been assigned exactly once

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